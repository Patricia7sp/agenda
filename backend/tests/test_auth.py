from sqlmodel import select

from app.api.v1.auth import _attempts
from app.core.config import settings
from app.models import LoginToken, User


def test_magic_link_cria_usuario_e_nao_vaza_existencia(client, session):
    r = client.post("/api/v1/auth/magic-link", json={"email": "nova@exemplo.com"})
    assert r.status_code == 200

    users = session.exec(select(User).where(User.email == "nova@exemplo.com")).all()
    assert len(users) == 1

    # Segunda chamada com e-mail já existente responde igual à primeira.
    r2 = client.post("/api/v1/auth/magic-link", json={"email": "nova@exemplo.com"})
    assert r2.status_code == 200
    assert set(r.json()) == set(r2.json())


def test_allowlist_server_side_nao_cria_usuario_para_email_bloqueado(client, session, monkeypatch):
    monkeypatch.setattr(settings, "allowed_emails", "permitido@exemplo.com")

    bloqueado = client.post("/api/v1/auth/magic-link", json={"email": "bloqueado@exemplo.com"})
    assert bloqueado.status_code == 200
    assert bloqueado.json()["dev_magic_link"] is None
    assert session.exec(select(User).where(User.email == "bloqueado@exemplo.com")).first() is None

    permitido = client.post("/api/v1/auth/magic-link", json={"email": "PERMITIDO@EXEMPLO.COM"})
    assert permitido.status_code == 200
    assert permitido.json()["dev_magic_link"]


def test_allowlist_e_revalidada_antes_de_consumir_token(client, monkeypatch, session):
    monkeypatch.setattr(settings, "allowed_emails", "permitido@exemplo.com")
    response = client.post("/api/v1/auth/magic-link", json={"email": "permitido@exemplo.com"})
    token = response.json()["dev_magic_link"].split("token=")[1]

    monkeypatch.setattr(settings, "allowed_emails", "outra@exemplo.com")
    assert client.post("/api/v1/auth/verify", json={"token": token}).status_code == 400
    assert session.exec(select(LoginToken)).one().used_at is None


def test_token_e_guardado_hasheado(client, session):
    client.post("/api/v1/auth/magic-link", json={"email": "hash@exemplo.com"})
    link = client.post("/api/v1/auth/magic-link", json={"email": "hash@exemplo.com"}).json()
    raw_token = link["dev_magic_link"].split("token=")[1]

    stored = session.exec(select(LoginToken)).all()
    assert stored
    assert all(t.token_hash != raw_token for t in stored)
    assert all(len(t.token_hash) == 64 for t in stored)


def test_magic_link_e_de_uso_unico(client):
    r = client.post("/api/v1/auth/magic-link", json={"email": "unico@exemplo.com"})
    token = r.json()["dev_magic_link"].split("token=")[1]

    assert client.post("/api/v1/auth/verify", json={"token": token}).status_code == 200
    segunda = client.post("/api/v1/auth/verify", json={"token": token})
    assert segunda.status_code == 400
    assert segunda.json()["code"] == "invalid_magic_link"


def test_token_invalido_e_rejeitado(client):
    r = client.post("/api/v1/auth/verify", json={"token": "token-invalido-com-tamanho-valido"})
    assert r.status_code == 400
    assert r.json() == {"detail": "Link inválido ou expirado", "code": "invalid_magic_link"}


def test_rate_limit_de_magic_link(client):
    email = "flood@exemplo.com"
    _attempts.pop(email, None)
    for _ in range(settings.magic_link_rate_limit_per_hour):
        assert client.post("/api/v1/auth/magic-link", json={"email": email}).json()["dev_magic_link"]
    # Acima do limite: continua 200 (não vaza), mas nenhum link novo é gerado.
    bloqueado = client.post("/api/v1/auth/magic-link", json={"email": email})
    assert bloqueado.status_code == 200
    assert bloqueado.json()["dev_magic_link"] is None
    # Em dev o motivo é explicitado, para o silêncio não virar beco sem saída.
    assert bloqueado.json()["dev_rate_limited"] is True


def test_me_exige_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer lixo"}).status_code == 401


def test_me_e_atualizacao_de_perfil(client, login):
    headers = login("perfil@exemplo.com")

    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["email"] == "perfil@exemplo.com"
    assert me["timezone"] == settings.default_timezone

    r = client.patch(
        "/api/v1/auth/me", headers=headers, json={"name": "Paty", "timezone": "Europe/Lisbon"}
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Paty"
    assert r.json()["timezone"] == "Europe/Lisbon"


def test_timezone_invalida_e_422(client, login):
    headers = login("tz@exemplo.com")
    r = client.patch("/api/v1/auth/me", headers=headers, json={"timezone": "Marte/Olympus"})
    assert r.status_code == 422
    assert r.json()["code"] == "invalid_timezone"
