from __future__ import annotations

import asyncio

import resend

from app.config import settings
from app.utils.audit import audit

VERIFY_PATH = "/verify-email"
RESET_PATH = "/reset-password"


async def _send(*, to: str, subject: str, text: str, kind: str) -> None:
    if not settings.resend_api_key:
        audit("email_send_failed", to=to, kind=kind, reason="resend_api_key_unset")
        return
    resend.api_key = settings.resend_api_key
    payload: resend.Emails.SendParams = {
        "from": settings.mail_from,
        "to": [to],
        "subject": subject,
        "text": text,
    }
    try:
        await asyncio.to_thread(resend.Emails.send, payload)
    except Exception as exc:
        audit("email_send_failed", to=to, kind=kind, error=str(exc))
        return
    audit("email_send_ok", to=to, kind=kind)


async def send_verification_email(to: str, token: str) -> None:
    url = f"{settings.app_base_url}{VERIFY_PATH}?token={token}"
    text = (
        "Hola,\n\n"
        "Confirma tu email haciendo clic en el siguiente enlace "
        "(válido durante 1 hora):\n\n"
        f"{url}\n\n"
        "Si no creaste una cuenta, ignora este mensaje."
    )
    await _send(to=to, subject="Confirma tu email", text=text, kind="verify")


async def send_reset_password_email(to: str, token: str) -> None:
    url = f"{settings.app_base_url}{RESET_PATH}?token={token}"
    text = (
        "Hola,\n\n"
        "Has solicitado restablecer tu contraseña. Usa el siguiente enlace "
        "(válido durante 1 hora):\n\n"
        f"{url}\n\n"
        "Si no fuiste tú, puedes ignorar este mensaje."
    )
    await _send(to=to, subject="Restablece tu contraseña", text=text, kind="reset")
