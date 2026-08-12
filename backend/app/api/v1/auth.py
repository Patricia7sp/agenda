from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Mapping, cast
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.core.config import settings
from app.core.deps import CurrentUser, SessionDep
from app.core.security import create_access_token, hash_token, new_magic_token
from app.models import LoginToken, User, utcnow
from app.schemas import (
    MagicLinkRequest,
    MagicLinkResponse,
    GoogleLoginRequest,
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


def _google_claims(credential: str) -> Mapping[str, object]:
    if not settings.google_client_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"detail": "Login com Google não configurado", "code": "google_not_configured"},
        )

    try:
        claims = cast(
            Mapping[str, object],
            google_id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.google_client_id,
            ),
        )
    except (ValueError, google_auth_exceptions.GoogleAuthError) as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Credencial Google inválida", "code": "invalid_google_credential"},
        ) from exc

    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Emissor Google inválido", "code": "invalid_google_issuer"},
        )
    if claims.get("email_verified") is not True:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"detail": "A conta Google precisa ter e-mail verificado", "code": "email_not_verified"},
        )
    return claims


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


@router.post("/google", response_model=TokenResponse)
def login_with_google(payload: GoogleLoginRequest, session: SessionDep) -> TokenResponse:
    """Valida a credencial do Google e emite o JWT próprio da Agenda."""
    claims = _google_claims(payload.credential)
    raw_email = claims.get("email")
    if not isinstance(raw_email, str):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Google não retornou um e-mail válido", "code": "google_email_missing"},
        )

    email = raw_email.strip().casefold()
    if not settings.is_email_allowed(email):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"detail": "Este e-mail não está autorizado para a Agenda", "code": "email_not_allowed"},
        )

    user = session.exec(select(User).where(User.email == email)).first()
    raw_name = claims.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else None
    if user is None:
        user = User(email=email, name=name, timezone=settings.default_timezone)
        session.add(user)
        session.commit()
        session.refresh(user)
    elif user.name is None and name is not None:
        user.name = name
        session.add(user)
        session.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserOut.model_validate(user, from_attributes=True),
    )


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
