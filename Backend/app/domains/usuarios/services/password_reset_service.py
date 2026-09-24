from __future__ import annotations

import hashlib
import os
import random
from datetime import datetime, timedelta, timezone

from flask import current_app

from app.database import db
from app.domains.usuarios.mail.mailer import send_password_reset_code
from app.domains.usuarios.security.passwords import hash_password
from app.models.password_reset_code import PasswordResetCode
from app.models.user import User


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_code(code: str) -> str:
    pepper = (
        current_app.config.get("PASSWORD_RESET_PEPPER")
        or current_app.config.get("JWT_SECRET_KEY")
        or os.getenv("PASSWORD_RESET_PEPPER")
        or "dev-reset-pepper"
    )
    raw = f"{code}:{pepper}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _generate_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def request_password_reset(email: str) -> dict:
    """
    Solicita reseteo de contraseña y envía código al mail.

    Respuesta intencionalmente uniforme para evitar enumeración de emails.

    Args:
        email: correo informado por usuario.

    Returns:
        Payload fijo de confirmación.
    """
    email_n = _normalize_email(email)
    user = User.query.filter_by(email=email_n, is_active=True).first()
    if user:
        code = _generate_code()
        reset = PasswordResetCode(
            user_id=user.id,
            code_hash=_hash_code(code),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            used_at=None,
        )
        db.session.add(reset)
        db.session.commit()
        try:
            send_password_reset_code(user.email, code)
        except Exception:
            current_app.logger.exception("No se pudo enviar email de recuperación")

    return {
        "ok": True,
        "message": "Si el correo existe, se enviará un código.",
    }


def confirm_password_reset(
    *,
    email: str,
    code: str,
    new_password: str,
) -> None:
    """
    Confirma código de reset y actualiza contraseña.

    Args:
        email: correo del usuario.
        code: código recibido por mail.
        new_password: nueva contraseña.

    Raises:
        ValueError: si email/código son inválidos o vencidos.
    """
    email_n = _normalize_email(email)
    user = User.query.filter_by(email=email_n, is_active=True).first()
    if not user:
        raise ValueError("Código inválido o vencido.")

    reset = (
        PasswordResetCode.query.filter_by(user_id=user.id, used_at=None)
        .order_by(PasswordResetCode.id.desc())
        .first()
    )
    if not reset:
        raise ValueError("Código inválido o vencido.")

    now_utc = datetime.now(timezone.utc)
    expires_at = reset.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now_utc:
        raise ValueError("Código inválido o vencido.")

    if reset.code_hash != _hash_code(code):
        raise ValueError("Código inválido o vencido.")

    user.password_hash = hash_password(new_password)
    reset.used_at = now_utc
    db.session.add(user)
    db.session.add(reset)
    db.session.commit()

