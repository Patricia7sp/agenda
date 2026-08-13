from datetime import date, datetime, timezone

API = "/api/v1/activities"


def criar(client, headers, **campos):
    payload = {"title": "Ligar para Ana", "scheduled_date": "2026-08-10", **campos}
    r = client.post(API, headers=headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_criacao_minima_aplica_defaults(client, login):
    """Critério G1: título + data e o resto vem de default."""
    headers = login("hoje@exemplo.com")
    a = criar(client, headers, title="Comprar pão")

    assert a["scheduled_time"] is None
    assert a["type"] == "task"
    assert a["priority"] == "normal"
    assert a["status"] == "pending"
    assert a["reminder_at"] is None
    assert a["reminder_offset_min"] is None
    assert a["postponed_count"] == 0


def test_lembrete_convertido_para_utc(client, login):
    """America/Sao_Paulo (UTC-3): 17:00 local vira 20:00Z."""
    headers = login("tz@exemplo.com")
    a = criar(client, headers, scheduled_time="17:00", reminder_offset_min=0)

    lembrete = datetime.fromisoformat(a["reminder_at"]).astimezone(timezone.utc)
    assert (lembrete.hour, lembrete.minute) == (20, 0)
    assert lembrete.date() == date(2026, 8, 10)


def test_lembrete_com_antecedencia(client, login):
    headers = login("offset@exemplo.com")
    a = criar(client, headers, scheduled_time="17:00", reminder_offset_min=15)

    lembrete = datetime.fromisoformat(a["reminder_at"]).astimezone(timezone.utc)
    assert (lembrete.hour, lembrete.minute) == (19, 45)
    assert a["reminder_offset_min"] == 15


def test_opcoes_de_antecedencia(client, login):
    headers = login("opcoes@exemplo.com")

    for offset, esperado in ((20, (19, 40)), (30, (19, 30)), (60, (19, 0))):
        a = criar(
            client,
            headers,
            title=f"Aviso {offset}",
            scheduled_time="17:00",
            reminder_offset_min=offset,
        )
        lembrete = datetime.fromisoformat(a["reminder_at"]).astimezone(timezone.utc)
        assert (lembrete.hour, lembrete.minute) == esperado
        assert a["reminder_offset_min"] == offset


def test_lembrete_respeita_timezone_do_usuario(client, login):
    headers = login("lisboa@exemplo.com")
    client.patch("/api/v1/auth/me", headers=headers, json={"timezone": "Europe/Lisbon"})
    a = criar(client, headers, scheduled_time="17:00", reminder_offset_min=0)

    # Lisboa em agosto está em UTC+1 → 16:00Z
    lembrete = datetime.fromisoformat(a["reminder_at"]).astimezone(timezone.utc)
    assert (lembrete.hour, lembrete.minute) == (16, 0)


def test_lembrete_sem_horario_e_422(client, login):
    headers = login("semhora@exemplo.com")
    r = client.post(
        API,
        headers=headers,
        json={"title": "X", "scheduled_date": "2026-08-10", "reminder_offset_min": 0},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "reminder_without_time"


def test_ordenacao_do_dia(client, login):
    """Com horário em ordem crescente; depois sem horário, por prioridade."""
    headers = login("ordem@exemplo.com")
    criar(client, headers, title="Sem hora baixa", priority="low")
    criar(client, headers, title="Sem hora alta", priority="high")
    criar(client, headers, title="Tarde", scheduled_time="17:00")
    criar(client, headers, title="Manhã", scheduled_time="09:00")

    titulos = [a["title"] for a in client.get(f"{API}?date=2026-08-10", headers=headers).json()]
    assert titulos == ["Manhã", "Tarde", "Sem hora alta", "Sem hora baixa"]


def test_concluir(client, login):
    headers = login("concluir@exemplo.com")
    a = criar(client, headers)

    r = client.post(f"{API}/{a['id']}/complete", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    assert r.json()["completed_at"] is not None


def test_adiar_e_acao_nao_status(client, login):
    headers = login("adiar@exemplo.com")
    a = criar(client, headers, scheduled_time="17:00", reminder_offset_min=0)

    r = client.post(
        f"{API}/{a['id']}/postpone",
        headers=headers,
        json={"scheduled_date": "2026-08-11", "scheduled_time": "17:00"},
    )
    assert r.status_code == 200
    adiada = r.json()

    assert adiada["scheduled_date"] == "2026-08-11"
    assert adiada["postponed_count"] == 1
    assert adiada["status"] == "pending"          # continua pendente
    assert adiada["reminder_sent"] is False       # lembrete reaberto
    assert adiada["reminder_offset_min"] == 0
    lembrete = datetime.fromisoformat(adiada["reminder_at"]).astimezone(timezone.utc)
    assert lembrete.date() == date(2026, 8, 11)

    # some de hoje, aparece amanhã
    assert client.get(f"{API}?date=2026-08-10", headers=headers).json() == []
    assert len(client.get(f"{API}?date=2026-08-11", headers=headers).json()) == 1


def test_edicao_de_horario_recalcula_lembrete(client, login):
    headers = login("edit@exemplo.com")
    a = criar(client, headers, scheduled_time="17:00", reminder_offset_min=0)

    r = client.patch(f"{API}/{a['id']}", headers=headers, json={"scheduled_time": "08:00"})
    assert r.status_code == 200
    lembrete = datetime.fromisoformat(r.json()["reminder_at"]).astimezone(timezone.utc)
    assert (lembrete.hour, lembrete.minute) == (11, 0)
    assert r.json()["reminder_sent"] is False


def test_edicao_e_adiamento_preservam_antecedencia(client, login):
    headers = login("preserva-offset@exemplo.com")
    a = criar(client, headers, scheduled_time="17:00", reminder_offset_min=30)

    editada = client.patch(
        f"{API}/{a['id']}", headers=headers, json={"scheduled_time": "08:00"}
    )
    assert editada.status_code == 200
    assert editada.json()["reminder_offset_min"] == 30
    lembrete = datetime.fromisoformat(editada.json()["reminder_at"]).astimezone(timezone.utc)
    assert (lembrete.hour, lembrete.minute) == (10, 30)

    adiada = client.post(
        f"{API}/{a['id']}/postpone",
        headers=headers,
        json={"scheduled_date": "2026-08-11", "scheduled_time": "09:00"},
    )
    assert adiada.status_code == 200
    assert adiada.json()["reminder_offset_min"] == 30
    lembrete = datetime.fromisoformat(adiada.json()["reminder_at"]).astimezone(timezone.utc)
    assert (lembrete.hour, lembrete.minute) == (11, 30)


def test_remover_lembrete_na_edicao(client, login):
    headers = login("semlembrete@exemplo.com")
    a = criar(client, headers, scheduled_time="17:00", reminder_offset_min=0)

    r = client.patch(f"{API}/{a['id']}", headers=headers, json={"reminder_offset_min": None})
    assert r.status_code == 200
    assert r.json()["reminder_at"] is None
    assert r.json()["reminder_offset_min"] is None


def test_remocao(client, login):
    headers = login("remover@exemplo.com")
    a = criar(client, headers)

    assert client.delete(f"{API}/{a['id']}", headers=headers).status_code == 204
    assert client.get(f"{API}/{a['id']}", headers=headers).status_code == 404


def test_summary_conta_por_dia(client, login):
    headers = login("summary@exemplo.com")
    a = criar(client, headers, title="A")
    criar(client, headers, title="B")
    criar(client, headers, title="C", scheduled_date="2026-08-12")
    client.post(f"{API}/{a['id']}/complete", headers=headers)

    dados = client.get(f"{API}/summary?from=2026-08-01&to=2026-08-31", headers=headers).json()
    assert dados == [
        {"date": "2026-08-10", "total": 2, "pending": 1},
        {"date": "2026-08-12", "total": 1, "pending": 1},
    ]


def test_isolamento_entre_usuarios(client, login):
    ana = login("ana2@exemplo.com")
    bob = login("bob2@exemplo.com")
    da_ana = criar(client, ana, title="Segredo da Ana")

    assert client.get(f"{API}?date=2026-08-10", headers=bob).json() == []
    assert client.get(f"{API}/{da_ana['id']}", headers=bob).status_code == 404
    assert client.patch(f"{API}/{da_ana['id']}", headers=bob, json={"title": "Hack"}).status_code == 404
    assert client.post(f"{API}/{da_ana['id']}/complete", headers=bob).status_code == 404
    assert client.delete(f"{API}/{da_ana['id']}", headers=bob).status_code == 404

    # E a atividade da Ana continua intacta
    assert client.get(f"{API}/{da_ana['id']}", headers=ana).json()["title"] == "Segredo da Ana"


def test_exige_autenticacao(client):
    assert client.get(f"{API}?date=2026-08-10").status_code == 401
    assert client.post(API, json={"title": "X", "scheduled_date": "2026-08-10"}).status_code == 401


def test_filtro_de_data_obrigatorio(client, login):
    headers = login("filtro@exemplo.com")
    r = client.get(API, headers=headers)
    assert r.status_code == 422
    assert r.json()["code"] == "missing_date_filter"
