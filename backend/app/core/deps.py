from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session

from app.core.db import get_session
from app.core.security import decode_access_token
from app.models import User

SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Credenciais ausentes", "code": "missing_token"},
        )
    user_id = decode_access_token(authorization.split(" ", 1)[1].strip())
    if user_id is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Token inválido ou expirado", "code": "invalid_token"},
        )
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Usuário não encontrado", "code": "user_not_found"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
