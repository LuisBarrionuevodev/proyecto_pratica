from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from flask import current_app


def _safe_log_exception(message: str, *args: object) -> None:
    """Loggea excepciones si hay contexto Flask activo."""
    try:
        current_app.logger.exception(message, *args)
    except Exception:
        # Evita romper ejecución si no hay app context (scripts/tests).
        if args:
            print(message % args)
        else:
            print(message)


def _safe_log_info(message: str, *args: object) -> None:
    """Loggea mensajes informativos con fallback a print."""
    try:
        current_app.logger.info(message, *args)
    except Exception:
        if args:
            print(message % args)
        else:
            print(message)


def _get_smtp_config() -> tuple[str, int, str, str, str]:
    """
    Obtiene configuración SMTP desde variables de entorno.

    Variables:
        SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
    """
    host = os.getenv("SMTP_HOST") or ""
    port_raw = os.getenv("SMTP_PORT", "587")
    user = os.getenv("SMTP_USER") or ""
    password = os.getenv("SMTP_PASS") or ""
    mail_from = os.getenv("SMTP_FROM") or ""
    try:
        port = int(port_raw)
    except ValueError:
        raise ValueError("SMTP_PORT debe ser un entero válido.")
    return host, port, user, password, mail_from


def send_email(to: str, subject: str, html: str) -> None:
    """
    Envía email HTML por SMTP con TLS (starttls).

    Args:
        to: destinatario.
        subject: asunto del correo.
        html: contenido HTML.

    Raises:
        ValueError: si falta configuración SMTP o parámetros requeridos.
        Exception: cualquier error de conexión/autenticación/envío.
    """
    if not to.strip():
        raise ValueError("El destinatario es requerido.")
    if not subject.strip():
        raise ValueError("El asunto es requerido.")
    if not html.strip():
        raise ValueError("El contenido HTML es requerido.")

    host, port, user, password, mail_from = _get_smtp_config()
    if not host or not mail_from or not user or not password:
        raise ValueError(
            "Configuración SMTP incompleta. Verificar SMTP_HOST, SMTP_PORT, "
            "SMTP_USER, SMTP_PASS y SMTP_FROM."
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = mail_from
    message["To"] = to
    message.set_content("Este correo requiere cliente con soporte HTML.")
    message.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(user, password)
            smtp.send_message(message)
    except Exception:
        _safe_log_exception("Error enviando email SMTP a %s", to)
        raise


def send_test_email(to: str) -> None:
    """
    Envía email de prueba para validar configuración SMTP.

    Args:
        to: destinatario de prueba.
    """
    html = """
    <div style="font-family:Arial,sans-serif;line-height:1.5;">
      <h2 style="margin-bottom:8px;">DIGITALIZA</h2>
      <p>Este es un email de prueba del sistema Digitaliza.</p>
      <p>Si recibiste este correo, el servicio SMTP funciona correctamente.</p>
    </div>
    """
    send_email(
        to=to,
        subject="Prueba SMTP - Digitaliza",
        html=html,
    )


def send_password_reset_code(email_to: str, code: str) -> None:
    """
    Envía por SMTP un código de recuperación.

    Si faltan variables SMTP, hace fallback a logging (modo dev).

    Args:
        email_to: correo destino.
        code: código de 6 dígitos en texto plano.
    """
    html = f"""
    <div style="font-family:Arial,sans-serif;line-height:1.5;">
      <h2 style="margin-bottom:8px;">DIGITALIZA</h2>
      <p>Tu código de recuperación es:</p>
      <p style="font-size:30px;font-weight:700;letter-spacing:5px;">{code}</p>
      <p>Expira en 15 minutos.</p>
    </div>
    """
    try:
        send_email(
            to=email_to,
            subject="Código de recuperación - Digitaliza",
            html=html,
        )
    except ValueError:
        # En dev, si faltan variables SMTP, deja traza de código para pruebas.
        _safe_log_info("[DEV MAILER] Reset code para %s: %s", email_to, code)
    except Exception:
        _safe_log_exception("No se pudo enviar email de recuperación a %s", email_to)
        raise

