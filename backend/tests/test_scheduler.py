"""Job de lembretes (§5) — o que faltava para a notificação chegar sozinha."""

from datetime import timedelta

import pytest
from sqlmodel import select

from app.models import Activity, ActivityStatus, PushSubscription, User, utcnow
from app.services import scheduler as scheduler_service
from app.services import webpush as webpush_service


@pytest.fixture
def enviados(monkeypatch):
    """Captura os pushes em vez de sair para a internet."""
    chamadas: list[dict] = []

    def fake_send(session, user_id, payload):
        chamadas.append({"user_id": user_id, "payload": payload})
        return webpush_service.PushResult(sent=1, failed=0, removed=0)

    monkeypatch.setattr(scheduler_service, "send_to_user", fake_send)
    return chamadas


@pytest.fixture
def emails(monkeypatch):
    enviados: list[tuple[str, str]] = []
    monkeypatch.setattr(
        scheduler_service,
        "send_email",
        lambda to, subject, text: enviados.append((to, text)) or True,
    )
    return enviados


def criar_usuario(session, email="scheduler@exemplo.com") -> User:
    user = User(email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def criar_atividade(session, user, *, minutos: int, **campos) -> Activity:
    """`minutos` negativo = lembrete já vencido."""
    from datetime import date, time

    campos.setdefault("scheduled_time", time(17, 0))
    activity = Activity(
        user_id=user.id,
        title=campos.pop("title", "Ligar para Ana"),
        scheduled_date=date(2026, 8, 10),
        reminder_at=utcnow() + timedelta(minutes=minutos),
        **campos,
    )
    session.add(activity)
    session.commit()
    session.refresh(activity)
    return activity


def test_lembrete_vencido_dispara_push(session, enviados, emails):
    user = criar_usuario(session)
    activity = criar_atividade(session, user, minutos=-1)

    assert scheduler_service.process_due_reminders(session) == 1
    assert len(enviados) == 1
    assert enviados[0]["payload"]["body"] == "17:00 — Ligar para Ana"
    assert enviados[0]["payload"]["url"] == f"/atividade/{activity.id}"

    session.refresh(activity)
    assert activity.reminder_sent is True
    assert emails == []


def test_lembrete_futuro_nao_dispara(session, enviados):
    user = criar_usuario(session)
    criar_atividade(session, user, minutos=5)

    assert scheduler_service.process_due_reminders(session) == 0
    assert enviados == []


def test_concluida_antes_do_horario_nao_notifica(session, enviados):
    """Critério de aceite: concluir antes do lembrete cancela o envio."""
    user = criar_usuario(session)
    criar_atividade(session, user, minutos=-1, status=ActivityStatus.completed)

    assert scheduler_service.process_due_reminders(session) == 0
    assert enviados == []


def test_nao_reenvia_o_mesmo_lembrete(session, enviados):
    user = criar_usuario(session)
    criar_atividade(session, user, minutos=-1)

    assert scheduler_service.process_due_reminders(session) == 1
    assert scheduler_service.process_due_reminders(session) == 0
    assert len(enviados) == 1


def test_sem_dispositivo_cai_no_email(session, emails, monkeypatch):
    monkeypatch.setattr(
        scheduler_service,
        "send_to_user",
        lambda *a, **k: webpush_service.PushResult(sent=0, failed=0, removed=0),
    )
    user = criar_usuario(session, "fallback@exemplo.com")
    criar_atividade(session, user, minutos=-1)

    assert scheduler_service.process_due_reminders(session) == 1
    assert emails == [("fallback@exemplo.com", "17:00 — Ligar para Ana")]


def test_falha_de_push_cai_no_email(session, emails, monkeypatch):
    monkeypatch.setattr(
        scheduler_service,
        "send_to_user",
        lambda *a, **k: webpush_service.PushResult(sent=0, failed=1, removed=0),
    )
    user = criar_usuario(session, "push-falhou@exemplo.com")
    activity = criar_atividade(session, user, minutos=-1)

    assert scheduler_service.process_due_reminders(session) == 1
    assert emails == [("push-falhou@exemplo.com", "17:00 — Ligar para Ana")]
    session.refresh(activity)
    assert activity.reminder_sent is True


def test_falha_total_reagenda_e_nao_perde_lembrete(session, monkeypatch, emails):
    """Falha de entrega mantém o lembrete pendente para retry com backoff."""
    monkeypatch.setattr(
        scheduler_service,
        "send_to_user",
        lambda *a, **k: webpush_service.PushResult(sent=0, failed=2, removed=0),
    )
    monkeypatch.setattr(scheduler_service, "send_email", lambda *a, **k: False)
    user = criar_usuario(session)
    activity = criar_atividade(session, user, minutos=-1)

    scheduler_service.process_due_reminders(session)
    session.refresh(activity)
    assert activity.reminder_sent is False
    assert activity.reminder_attempts == 1
    assert activity.reminder_next_attempt_at is not None


def test_atividade_sem_horario_usa_rotulo_do_dia(session, enviados):
    user = criar_usuario(session)
    criar_atividade(session, user, minutos=-1, scheduled_time=None, title="Comprar pão")

    scheduler_service.process_due_reminders(session)
    assert enviados[0]["payload"]["body"] == "Hoje — Comprar pão"


def test_isolamento_por_usuario_no_envio(session, enviados):
    ana = criar_usuario(session, "ana-sched@exemplo.com")
    bob = criar_usuario(session, "bob-sched@exemplo.com")
    criar_atividade(session, ana, minutos=-1, title="Da Ana")
    criar_atividade(session, bob, minutos=-1, title="Do Bob")

    scheduler_service.process_due_reminders(session)

    destinos = {c["user_id"]: c["payload"]["body"] for c in enviados}
    assert destinos[ana.id].endswith("Da Ana")
    assert destinos[bob.id].endswith("Do Bob")


def test_adiar_reabre_o_lembrete(client, login, session, enviados):
    """Depois de enviado, adiar precisa fazer o lembrete disparar de novo."""
    headers = login("readiar@exemplo.com")
    r = client.post(
        "/api/v1/activities",
        headers=headers,
        json={
            "title": "Consulta",
            "scheduled_date": "2026-08-10",
            "scheduled_time": "17:00",
            "reminder_offset_min": 0,
        },
    )
    activity_id = r.json()["id"]

    activity = session.exec(select(Activity).where(Activity.id == activity_id)).one()
    activity.reminder_at = utcnow() - timedelta(minutes=1)
    session.add(activity)
    session.commit()

    assert scheduler_service.process_due_reminders(session) == 1

    client.post(
        f"/api/v1/activities/{activity_id}/postpone",
        headers=headers,
        json={"scheduled_date": "2026-08-11", "scheduled_time": "09:00"},
    )
    session.expire_all()
    activity = session.exec(select(Activity).where(Activity.id == activity_id)).one()
    assert activity.reminder_sent is False


def test_subscription_do_usuario_e_encontrada(session):
    """Sanidade do vínculo usuário → dispositivos."""
    user = criar_usuario(session, "subs@exemplo.com")
    session.add(
        PushSubscription(
            user_id=user.id, endpoint="https://push.example.com/z", p256dh="k", auth="a"
        )
    )
    session.commit()

    subs = session.exec(
        select(PushSubscription).where(PushSubscription.user_id == user.id)
    ).all()
    assert len(subs) == 1
