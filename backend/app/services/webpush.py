"""Envio de Web Push (VAPID) e limpeza de subscriptions expiradas.

Regra do §5: resposta 404/410 do push service → deletar a subscription.
"""

import json
import logging
import uuid
from dataclasses import dataclass

from py_vapid import VapidException
from pywebpush import WebPushException, webpush
from sqlmodel import Session, select

from app.core.config import settings
from app.models import PushSubscription

log = logging.getLogger(__name__)


@dataclass
class PushResult:
    sent: int
    failed: int
    removed: int

    @property
    def delivered(self) -> bool:
        return self.sent > 0


def send_to_user(session: Session, user_id: uuid.UUID, payload: dict[str, str]) -> PushResult:
    """Envia até o limite de dispositivos do usuário. Nunca levanta exceção."""
    if not settings.push_enabled:
        log.warning("VAPID não configurado — push ignorado para user %s", user_id)
        return PushResult(0, 0, 0)

    subs = session.exec(
        select(PushSubscription)
        .where(PushSubscription.user_id == user_id)
        .order_by(PushSubscription.created_at)
        .limit(settings.max_subscriptions_per_user)
    ).all()

    sent = failed = removed = 0
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps(payload),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject_uri},
                timeout=10,
            )
            sent += 1
        except (VapidException, WebPushException, OSError, ValueError) as exc:
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None)
            if status in (404, 410):
                session.delete(sub)
                removed += 1
                log.info("Subscription expirada removida (%s): %s", status, sub.endpoint[:60])
            else:
                failed += 1
                log.error("Falha no push para %s: %s", sub.endpoint[:60], exc)

    if removed:
        session.commit()
    return PushResult(sent, failed, removed)
