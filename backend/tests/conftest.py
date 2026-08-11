"""Configuração dos testes.

Os testes rodam num banco **separado** (`<banco>_test`), criado e migrado
automaticamente. Nada aqui toca o banco de desenvolvimento — as tabelas são
limpas entre os casos, e apontar isso para o banco real apagaria seus dados.
"""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

# Precisa acontecer ANTES de qualquer import de `app`: as configurações são
# lidas na importação e o engine é criado junto com elas.
_dev_url = make_url(
    os.environ.get("DATABASE_URL", "postgresql+psycopg://agenda:agenda@db:5432/agenda")
)
_test_url = _dev_url.set(database=f"{_dev_url.database}_test")

_admin = create_engine(_dev_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
with _admin.connect() as conn:
    existe = conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :nome"), {"nome": _test_url.database}
    ).first()
    if not existe:
        conn.execute(text(f'CREATE DATABASE "{_test_url.database}"'))
_admin.dispose()

os.environ["DATABASE_URL"] = _test_url.render_as_string(hide_password=False)

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, delete  # noqa: E402

from app.core.db import engine, get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Activity, LoginToken, PushSubscription, User  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrar_banco_de_teste():
    """Aplica as migrações no banco de teste — o mesmo schema da produção."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(config, "head")
    yield


@pytest.fixture(autouse=True)
def clean_db(migrar_banco_de_teste):
    with Session(engine) as session:
        for model in (LoginToken, PushSubscription, Activity, User):
            session.exec(delete(model))
        session.commit()
    yield


@pytest.fixture
def session():
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def login(client):
    """Faz o fluxo completo de magic link e devolve o header de autorização."""

    def _login(email: str) -> dict[str, str]:
        r = client.post("/api/v1/auth/magic-link", json={"email": email})
        assert r.status_code == 200, r.text
        link = r.json()["dev_magic_link"]
        assert link, "APP_ENV precisa ser 'dev' e sem provedor de e-mail para os testes"
        token = link.split("token=")[1]
        r = client.post("/api/v1/auth/verify", json={"token": token})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _login
