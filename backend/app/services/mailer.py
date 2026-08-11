"""Envio de e-mail: Resend (default documentado) ou SMTP genérico (self-host).

Sem nenhum dos dois configurado, o e-mail é apenas logado — suficiente para dev.
"""

import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


def send_email(to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Retorna True se o e-mail foi entregue a um provedor de verdade."""
    if settings.resend_api_key:
        return _send_resend(to, subject, text, html)
    if settings.smtp_host:
        return _send_smtp(to, subject, text, html)
    log.warning("Nenhum provedor de e-mail configurado. E-mail para %s:\n%s\n%s", to, subject, text)
    return False


def _send_resend(to: str, subject: str, text: str, html: str | None) -> bool:
    payload = {"from": settings.mail_from, "to": [to], "subject": subject, "text": text}
    if html:
        payload["html"] = html
    try:
        r = httpx.post(
            "https://api.resend.com/emails",
            json=payload,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        log.error("Falha ao enviar e-mail via Resend para %s: %s", to, exc)
        return False


def _send_smtp(to: str, subject: str, text: str, html: str | None) -> bool:
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        log.error("Falha ao enviar e-mail via SMTP para %s: %s", to, exc)
        return False


def send_magic_link(to: str, link: str) -> bool:
    text = (
        "Seu link de acesso à Agenda (válido por "
        f"{settings.magic_link_expires_min} minutos):\n\n{link}\n\n"
        "Se você não pediu este link, ignore este e-mail."
    )
    html = (
        f'<p>Seu link de acesso à Agenda (válido por {settings.magic_link_expires_min} minutos):</p>'
        f'<p><a href="{link}">Entrar na Agenda</a></p>'
        "<p>Se você não pediu este link, ignore este e-mail.</p>"
    )
    return send_email(to, "Seu link de acesso à Agenda", text, html)
