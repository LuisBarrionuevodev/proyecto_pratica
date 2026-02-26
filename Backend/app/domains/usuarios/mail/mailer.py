from __future__ import annotations

import smtplib
from email.message import EmailMessage

from flask import current_app


def send_password_reset_code(email_to: str, code: str) -> None:
    """
    Envía por SMTP un código de recuperación.

    Si faltan variables SMTP, hace fallback a logging (modo dev).

    Args:
        email_to: correo destino.
        code: código de 6 dígitos en texto plano.
    """
    host = current_app.config.get("SMTP_HOST")
    port = int(current_app.config.get("SMTP_PORT", 587))
    user = current_app.config.get("SMTP_USER")
    password = current_app.config.get("SMTP_PASS")
    mail_from = current_app.config.get("SMTP_FROM")

    if not host or not mail_from:
        current_app.logger.info(
            "[DEV MAILER] Reset code para %s: %s",
            email_to,
            code,
        )
        return

    message = EmailMessage()
    message["Subject"] = "Codigo de recuperacion de cuenta"
    message["From"] = mail_from
    message["To"] = email_to
    message.set_content(
        "Tu codigo de recuperacion de clave es: "
        f"{code}\n\n"
        "Este codigo vence en 15 minutos."
    )

    with smtplib.SMTP(host, port, timeout=10) as smtp:
        smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(message)

