"""Pipeline de envio contra um push service falso rodando em localhost.

Cobre o critério de aceite: push service devolvendo 410 → subscription removida.
"""

import base64
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid import Vapid, VapidException
from sqlmodel import select

from app.core.config import settings
from app.models import PushSubscription, User
from app.services import webpush as webpush_service

recebidos: list[tuple[str, bytes]] = []


class FakePushService(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", 0))
        body = self.rfile.read(length)
        recebidos.append((self.path, body))
        # /gone simula uma subscription expirada
        status = 410 if self.path.startswith("/gone") else 201
        self.send_response(status)
        self.end_headers()

    def log_message(self, *args) -> None:  # silencia o log do http.server
        pass


@pytest.fixture(scope="module")
def push_service():
    server = HTTPServer(("127.0.0.1", 0), FakePushService)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture(autouse=True)
def vapid_configurado(monkeypatch):
    vapid = Vapid()
    vapid.generate_keys()
    raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    monkeypatch.setattr(
        settings, "vapid_private_key", base64.urlsafe_b64encode(raw).decode().rstrip("=")
    )
    monkeypatch.setattr(settings, "vapid_public_key", "chave-publica-de-teste")
    monkeypatch.setattr(settings, "vapid_subject", "mailto:testes@exemplo.com")


def _client_keys() -> tuple[str, str]:
    """Par de chaves do 'navegador' — p256dh precisa ser válido para a criptografia."""
    key = ec.generate_private_key(ec.SECP256R1())
    p256dh = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    b64 = lambda raw: base64.urlsafe_b64encode(raw).decode().rstrip("=")  # noqa: E731
    return b64(p256dh), b64(b"0123456789abcdef")


def _criar_usuario_com_sub(session, endpoint: str) -> User:
    user = User(email=f"push-{endpoint[-6:]}@exemplo.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    p256dh, auth = _client_keys()
    session.add(
        PushSubscription(user_id=user.id, endpoint=endpoint, p256dh=p256dh, auth=auth)
    )
    session.commit()
    return user


def test_push_entregue_ao_push_service(session, push_service):
    recebidos.clear()
    user = _criar_usuario_com_sub(session, f"{push_service}/ok/abc")

    result = webpush_service.send_to_user(session, user.id, {"title": "Oi", "body": "corpo"})

    assert result.sent == 1
    assert result.failed == 0
    assert result.delivered is True
    assert len(recebidos) == 1
    caminho, corpo = recebidos[0]
    assert caminho == "/ok/abc"
    assert corpo  # payload criptografado, não legível em texto puro
    assert b"corpo" not in corpo


def test_410_remove_a_subscription(session, push_service):
    recebidos.clear()
    user = _criar_usuario_com_sub(session, f"{push_service}/gone/xyz")

    result = webpush_service.send_to_user(session, user.id, {"title": "Oi", "body": "corpo"})

    assert result.sent == 0
    assert result.removed == 1
    assert result.delivered is False
    restantes = session.exec(
        select(PushSubscription).where(PushSubscription.user_id == user.id)
    ).all()
    assert restantes == []


def test_sem_vapid_nao_envia(session, push_service, monkeypatch):
    recebidos.clear()
    user = _criar_usuario_com_sub(session, f"{push_service}/ok/sem-vapid")
    monkeypatch.setattr(settings, "vapid_private_key", "")

    result = webpush_service.send_to_user(session, user.id, {"title": "Oi", "body": "corpo"})

    assert (result.sent, result.failed, result.removed) == (0, 0, 0)
    assert recebidos == []


def test_subject_sem_mailto_e_normalizado(session, push_service, monkeypatch):
    recebidos.clear()
    user = _criar_usuario_com_sub(session, f"{push_service}/ok/subject-normalizado")
    monkeypatch.setattr(settings, "vapid_subject", "admin@exemplo.com")

    result = webpush_service.send_to_user(
        session, user.id, {"title": "Oi", "body": "corpo"}
    )

    assert result.sent == 1
    assert result.failed == 0


def test_erro_vapid_fica_isolado_e_nao_interrompe_pipeline(
    session, push_service, monkeypatch
):
    user = _criar_usuario_com_sub(session, f"{push_service}/ok/vapid-invalido")

    def assinatura_invalida(**kwargs):
        raise VapidException("subject inválido")

    monkeypatch.setattr(webpush_service, "webpush", assinatura_invalida)

    result = webpush_service.send_to_user(
        session, user.id, {"title": "Oi", "body": "corpo"}
    )

    assert result.sent == 0
    assert result.failed == 1
    assert result.delivered is False
