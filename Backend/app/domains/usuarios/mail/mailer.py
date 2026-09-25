from __future__ import annotations

import json
import os
import smtplib
from email.message import EmailMessage
from typing import Any

import requests
from flask import current_app

MAILJET_SEND_URL = "https://api.mailjet.com/v3.1/send"
EMAIL_TRANSPORT_TIMEOUT_SEC = 20
MAILJET_REQUEST_TIMEOUT_SEC = EMAIL_TRANSPORT_TIMEOUT_SEC
_HTML_TEXT_FALLBACK = "Este correo requiere cliente con soporte HTML."


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


def _safe_log_error(message: str, *args: object) -> None:
    """Loggea errores con fallback a print."""
    try:
        current_app.logger.error(message, *args)
    except Exception:
        if args:
            print(message % args)
        else:
            print(message)


def _get_mail_provider() -> str:
    """Resuelve el proveedor de correo desde MAIL_PROVIDER (default: smtp)."""
    return (os.getenv("MAIL_PROVIDER") or "smtp").strip().lower()


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


def _get_mailjet_config() -> tuple[str, str, str, str]:
    """
    Obtiene configuración Mailjet Send API desde variables de entorno.

    Variables obligatorias: MAILJET_API_KEY, MAILJET_SECRET_KEY, MAILJET_FROM_EMAIL.
    MAILJET_FROM_NAME default: Digitaliza.

    Returns:
        (api_key, secret_key, from_email, from_name)

    Raises:
        ValueError: si falta alguna variable obligatoria.
    """
    api_key = (os.getenv("MAILJET_API_KEY") or "").strip()
    secret_key = (os.getenv("MAILJET_SECRET_KEY") or "").strip()
    from_email = (os.getenv("MAILJET_FROM_EMAIL") or "").strip()
    from_name_raw = os.getenv("MAILJET_FROM_NAME")
    if from_name_raw is None or not str(from_name_raw).strip():
        from_name = "Digitaliza"
    else:
        from_name = str(from_name_raw).strip()

    if not api_key:
        raise ValueError(
            "MAILJET_API_KEY es requerido cuando MAIL_PROVIDER=mailjet."
        )
    if not secret_key:
        raise ValueError(
            "MAILJET_SECRET_KEY es requerido cuando MAIL_PROVIDER=mailjet."
        )
    if not from_email:
        raise ValueError(
            "MAILJET_FROM_EMAIL es requerido cuando MAIL_PROVIDER=mailjet."
        )
    return api_key, secret_key, from_email, from_name


def _sanitize_mailjet_log_fragment(text: str, max_len: int = 500) -> str:
    """Acota y elimina posibles secretos de un fragmento de respuesta para logs."""
    if not text:
        return ""
    lowered = text.lower()
    for marker in ("apikey", "secret", "authorization", "basic "):
        if marker in lowered:
            return "[respuesta omitida: posible dato sensible]"
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def _validate_mailjet_response_body(data: dict[str, Any]) -> None:
    """
    Valida el cuerpo JSON de Mailjet v3.1 tras HTTP 2xx.

    Raises:
        RuntimeError: si el primer mensaje indica fallo explícito.
    """
    messages = data.get("Messages")
    if not isinstance(messages, list) or not messages:
        return
    first = messages[0]
    if not isinstance(first, dict):
        return
    status = str(first.get("Status") or "").strip().lower()
    if status and status != "success":
        raise RuntimeError(
            f"Mailjet rechazó el envío (Status={status})."
        )
    errors = first.get("Errors")
    if errors:
        raise RuntimeError("Mailjet reportó errores en el envío del mensaje.")


def _send_email_smtp(to: str, subject: str, html: str) -> None:
    """
    Envía email HTML por SMTP con TLS (starttls).

    Args:
        to: destinatario.
        subject: asunto del correo.
        html: contenido HTML.

    Raises:
        ValueError: si falta configuración SMTP.
        Exception: cualquier error de conexión/autenticación/envío.
    """
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
    message.set_content(_HTML_TEXT_FALLBACK)
    message.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=EMAIL_TRANSPORT_TIMEOUT_SEC) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(user, password)
            smtp.send_message(message)
    except Exception:
        _safe_log_exception("Error enviando email SMTP a %s", to)
        raise


def _send_email_mailjet(to: str, subject: str, html: str) -> None:
    """
    Envía email HTML vía Mailjet Send API v3.1 (HTTPS).

    Args:
        to: destinatario.
        subject: asunto del correo.
        html: contenido HTML.

    Raises:
        ValueError: si falta configuración Mailjet.
        requests.RequestException: timeout o error de conexión HTTP.
        RuntimeError: respuesta HTTP no exitosa o rechazo explícito en JSON.
    """
    api_key, secret_key, from_email, from_name = _get_mailjet_config()
    payload = {
        "Messages": [
            {
                "From": {"Email": from_email, "Name": from_name},
                "To": [{"Email": to}],
                "Subject": subject,
                "TextPart": _HTML_TEXT_FALLBACK,
                "HTMLPart": html,
            }
        ]
    }

    try:
        response = requests.post(
            MAILJET_SEND_URL,
            json=payload,
            auth=(api_key, secret_key),
            timeout=MAILJET_REQUEST_TIMEOUT_SEC,
        )
    except requests.Timeout:
        _safe_log_error(
            "Timeout enviando email Mailjet a %s (>%ss)",
            to,
            MAILJET_REQUEST_TIMEOUT_SEC,
        )
        raise
    except requests.ConnectionError:
        _safe_log_error("Error de conexión enviando email Mailjet a %s", to)
        raise

    if not (200 <= response.status_code < 300):
        body_fragment = _sanitize_mailjet_log_fragment(response.text)
        _safe_log_error(
            "Mailjet HTTP %s al enviar a %s: %s",
            response.status_code,
            to,
            body_fragment,
        )
        raise RuntimeError(
            f"Mailjet respondió HTTP {response.status_code}; el envío no se completó."
        )

    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError):
        data = None

    if isinstance(data, dict):
        _validate_mailjet_response_body(data)
        messages = data.get("Messages")
        if isinstance(messages, list) and messages:
            first = messages[0]
            if isinstance(first, dict):
                message_id = first.get("MessageID") or first.get("MessageUUID")
                if message_id is not None:
                    _safe_log_info(
                        "Email Mailjet enviado a %s (MessageID=%s)",
                        to,
                        message_id,
                    )


def send_email(to: str, subject: str, html: str) -> None:
    """
    Envía email HTML usando el proveedor configurado (SMTP o Mailjet).

    Args:
        to: destinatario.
        subject: asunto del correo.
        html: contenido HTML.

    Raises:
        ValueError: si faltan parámetros, configuración o MAIL_PROVIDER no soportado.
        Exception: errores de transporte del proveedor activo.
    """
    if not to.strip():
        raise ValueError("El destinatario es requerido.")
    if not subject.strip():
        raise ValueError("El asunto es requerido.")
    if not html.strip():
        raise ValueError("El contenido HTML es requerido.")

    provider = _get_mail_provider()
    if provider == "smtp":
        _send_email_smtp(to, subject, html)
    elif provider == "mailjet":
        _send_email_mailjet(to, subject, html)
    else:
        raise ValueError("MAIL_PROVIDER no soportado")


def send_test_email(to: str) -> None:
    """
    Envía email de prueba para validar configuración de correo.

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
    Envía por correo un código de recuperación.

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
