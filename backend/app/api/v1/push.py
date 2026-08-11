import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.core.deps import CurrentUser, SessionDep
from app.models import PushSubscription
from app.schemas import (
    PushTestRequest,
    PushTestResponse,
    SubscriptionDelete,
    SubscriptionIn,
    SubscriptionOut,
    VapidKeyOut,
)
from app.services.mailer import send_email
from app.services.webpush import send_to_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/vapid-public-key", response_model=VapidKeyOut)
def vapid_public_key() -> VapidKeyOut:
    if not settings.push_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"detail": "VAPID não configurado no servidor", "code": "vapid_missing"},
        )
    return VapidKeyOut(public_key=settings.vapid_public_key)


@router.post("/subscriptions", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
def upsert_subscription(
    payload: SubscriptionIn,
    user: CurrentUser,
    session: SessionDep,
    request: Request,
) -> SubscriptionOut:
    """Upsert por endpoint — o mesmo dispositivo re-registra a cada abertura do app."""
    user_agent = payload.user_agent or request.headers.get("user-agent")
    sub = session.exec(
        select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint)
    ).first()

    if sub is None:
        sub = PushSubscription(
            user_id=user.id,
            endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
            user_agent=user_agent,
        )
    else:
        # O endpoint é único global; se mudou de dono, o dono atual assume.
        sub.user_id = user.id
        sub.p256dh = payload.keys.p256dh
        sub.auth = payload.keys.auth
        sub.user_agent = user_agent

    session.add(sub)
    session.commit()
    session.refresh(sub)
    return SubscriptionOut.model_validate(sub, from_attributes=True)


@router.delete("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    payload: SubscriptionDelete,
    user: CurrentUser,
    session: SessionDep,
) -> Response:
    sub = session.exec(
        select(PushSubscription)
        .where(PushSubscription.endpoint == payload.endpoint)
        .where(PushSubscription.user_id == user.id)
    ).first()
    if sub is not None:
        session.delete(sub)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(user: CurrentUser, session: SessionDep) -> list[SubscriptionOut]:
    subs = session.exec(
        select(PushSubscription).where(PushSubscription.user_id == user.id)
        .order_by(PushSubscription.created_at)
        .limit(settings.max_subscriptions_per_user)
    ).all()
    return [SubscriptionOut.model_validate(s, from_attributes=True) for s in subs]


def _deliver(user_id: uuid.UUID, email: str, title: str, body: str) -> PushTestResponse:
    """Mesmo caminho que o scheduler de lembretes usará na etapa 3."""
    with Session(engine) as session:
        result = send_to_user(
            session,
            user_id,
            {"title": title, "body": body, "tag": "spike-test", "url": "/"},
        )
    email_fallback = False
    if not result.delivered:
        email_fallback = send_email(email, title, body)
    return PushTestResponse(
        sent=result.sent,
        failed=result.failed,
        removed=result.removed,
        email_fallback=email_fallback,
    )


@router.post("/test", response_model=PushTestResponse)
async def send_test_push(payload: PushTestRequest, user: CurrentUser) -> PushTestResponse:
    """Endpoint de envio do spike (etapa 0): dispara um push para todos os dispositivos.

    Com `delay_seconds > 0` o envio é agendado, para você fechar o app e validar
    a entrega com o PWA em segundo plano — o cenário que de fato importa no iOS.
    """
    if not settings.is_dev:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    user_id, email = user.id, user.email

    if payload.delay_seconds == 0:
        return await run_in_threadpool(_deliver, user_id, email, payload.title, payload.body)

    async def _later() -> None:
        try:
            await asyncio.sleep(payload.delay_seconds)
            result = await run_in_threadpool(_deliver, user_id, email, payload.title, payload.body)
            log.info("Push agendado enviado para %s: %s", email, result)
        except (OSError, RuntimeError, ValueError) as exc:
            log.error("Falha no push agendado para %s: %s", email, exc)

    asyncio.create_task(_later())
    return PushTestResponse(scheduled_in=payload.delay_seconds)
