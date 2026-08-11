from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.core.config import settings
from app.core.deps import CurrentUser, SessionDep
from app.core.security import create_access_token, hash_token, new_magic_token
from app.models import LoginToken, User, utcnow
from app.schemas import (
    MagicLinkRequest,
    MagicLinkResponse,
    TokenResponse,
    UserOut,
    UserUpdate,
    VerifyRequest,
)
from app.services.mailer import send_magic_link

router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limit em memória: suficiente para um processo só (uso pessoal).
# Ao escalar para múltiplos workers, trocar por Redis ou por contagem em login_token.
_attempts: dict[str, deque[datetime]] = defaultdict(deque)


def _rate_limited(email: str) -> bool:
    now = datetime.now(timezone.utc)
    window = _attempts[email]
    while window and window[0] < now - timedelta(hours=1):
        window.popleft()
    if len(window) >= settings.magic_link_rate_limit_per_hour:
        return True
    window.append(now)
    return False


@router.post("/magic-link", response_model=MagicLinkResponse)
def request_magic_link(payload: MagicLinkRequest, session: SessionDep) -> MagicLinkResponse:
    """Sempre 200 — não vaza a existência da conta."""
    email = str(payload.email).strip().casefold()
    if not settings.is_email_allowed(email):
        return MagicLinkResponse()
    if _rate_limited(email):
        return MagicLinkResponse(dev_rate_limited=settings.is_dev)

    user = session.exec(select(User).where(User.email == email)).first()
    if user is None:
        user = User(email=email, timezone=settings.default_timezone)
        session.add(user)
        session.commit()
        session.refresh(user)

    token, token_hash = new_magic_token()
    session.add(
        LoginToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=utcnow() + timedelta(minutes=settings.magic_link_expires_min),
        )
    )
    session.commit()

    link = f"{settings.frontend_url}/auth/callback?token={quote(token)}"
    delivered = send_magic_link(email, link)

    if not delivered and settings.is_dev:
        return MagicLinkResponse(dev_magic_link=link)
    return MagicLinkResponse()


@router.post("/verify", response_model=TokenResponse)
def verify(payload: VerifyRequest, session: SessionDep) -> TokenResponse:
    token_hash = hash_token(payload.token)
    login_token = session.exec(
        select(LoginToken).where(LoginToken.token_hash == token_hash)
    ).first()

    invalid = HTTPException(
        status.HTTP_400_BAD_REQUEST,
        detail={"detail": "Link inválido ou expirado", "code": "invalid_magic_link"},
    )
    if login_token is None or login_token.used_at is not None:
        raise invalid

    expires_at = login_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < utcnow():
        raise invalid

    user = session.get(User, login_token.user_id)
    if user is None or not settings.is_email_allowed(user.email):
        raise invalid

    login_token.used_at = utcnow()
    session.add(login_token)
    session.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserOut.model_validate(user, from_attributes=True),
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user, from_attributes=True)


@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, user: CurrentUser, session: SessionDep) -> UserOut:
    if payload.name is not None:
        user.name = payload.name
    if payload.timezone is not None:
        try:
            ZoneInfo(payload.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"detail": "Timezone inválida", "code": "invalid_timezone"},
            )
        user.timezone = payload.timezone
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserOut.model_validate(user, from_attributes=True)
