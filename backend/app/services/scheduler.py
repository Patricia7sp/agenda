"""Disparo confiável de lembretes com claim, retry e fallback de e-mail."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models import Activity, ActivityStatus, User, utcnow
from app.services.mailer import send_email
from app.services.webpush import PushResult, send_to_user

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReminderCandidate:
    activity_id: uuid.UUID
    user_id: uuid.UUID
    email: str | None
    body: str


def due_reminders_query(now: datetime):
    return (
        select(Activity)
        .where(Activity.reminder_at.is_not(None))
        .where(Activity.reminder_at <= now)
        .where(Activity.reminder_sent.is_(False))
        .where(Activity.status == ActivityStatus.pending)
        .where(Activity.reminder_attempts < settings.reminder_max_attempts)
        .where(
            or_(
                Activity.reminder_next_attempt_at.is_(None),
                Activity.reminder_next_attempt_at <= now,
            )
        )
        .order_by(Activity.reminder_at)
        .with_for_update(skip_locked=True)
        .limit(settings.reminder_batch_size)
    )


def notification_body(activity: Activity) -> str:
    hora = activity.scheduled_time.strftime("%H:%M") if activity.scheduled_time else "Hoje"
    return f"{hora} — {activity.title}"


def _retry_at(now: datetime, attempt: int) -> datetime:
    delay_minutes = min(60, 2 ** max(attempt - 1, 0))
    return now + timedelta(minutes=delay_minutes)


def process_due_reminders(session: Session, now: datetime | None = None) -> int:
    """Reivindica lembretes e entrega fora da transação que mantém o lock."""
    now = now or utcnow()
    vencidos = session.exec(due_reminders_query(now)).all()
    if not vencidos:
        return 0

    candidates: list[ReminderCandidate] = []
    for activity in vencidos:
        user = session.get(User, activity.user_id)
        activity.reminder_attempts += 1
        activity.reminder_next_attempt_at = _retry_at(now, activity.reminder_attempts)
        activity.reminder_last_error = None
        session.add(activity)
        candidates.append(
            ReminderCandidate(
                activity_id=activity.id,
                user_id=activity.user_id,
                email=user.email if user else None,
                body=notification_body(activity),
            )
        )
    session.commit()

    for candidate in candidates:
        result = PushResult(sent=0, failed=0, removed=0)
        with Session(engine) as delivery_session:
            result = send_to_user(
                delivery_session,
                candidate.user_id,
                {
                    "title": "Agenda",
                    "body": candidate.body,
                    "tag": str(candidate.activity_id),
                    "url": f"/atividade/{candidate.activity_id}",
                },
            )

        delivered = result.delivered
        if not delivered and candidate.email:
            delivered = send_email(candidate.email, "Lembrete da Agenda", candidate.body)

        with Session(engine) as update_session:
            activity = update_session.get(Activity, candidate.activity_id)
            if activity is None:
                continue
            if delivered:
                activity.reminder_sent = True
                activity.reminder_next_attempt_at = None
                activity.reminder_last_error = None
            elif activity.reminder_attempts >= settings.reminder_max_attempts:
                activity.reminder_last_error = "delivery_failed"
            else:
                activity.reminder_last_error = "delivery_retry_pending"
            update_session.add(activity)
            update_session.commit()

        log.info(
            "Lembrete de %s: push %d enviados, %d falhas, %d removidas, entregue=%s",
            candidate.activity_id,
            result.sent,
            result.failed,
            result.removed,
            delivered,
        )

    return len(candidates)


def run_tick() -> None:
    """Executa um tick sem deixar falha de banco matar o scheduler."""
    try:
        with Session(engine) as session:
            tratados = process_due_reminders(session)
        if tratados:
            log.info("Tick de lembretes: %d atividade(s) processada(s)", tratados)
    except (SQLAlchemyError, OSError, ValueError) as exc:
        log.exception("Falha no tick de lembretes: %s", exc)
