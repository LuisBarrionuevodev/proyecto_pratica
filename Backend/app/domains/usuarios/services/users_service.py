from __future__ import annotations

from typing import Optional

from sqlalchemy import or_

from app.database import db
from app.domains.usuarios.security.passwords import hash_password
from app.models.profile import Profile
from app.models.user import User


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_username(username: str) -> str:
    return username.strip()


def _ensure_profile(user: User) -> Profile:
    """Asegura que el usuario tenga profile 1:1 y lo retorna."""
    if user.profile:
        return user.profile
    profile = Profile(user_id=user.id, nickname=None, avatar_key="avatar1")
    db.session.add(profile)
    db.session.flush()
    return profile


def list_users_admin() -> list[dict]:
    """
    Lista usuarios para administración.

    Returns:
        Lista serializada de usuarios.
    """
    users = User.query.order_by(User.id.asc()).all()
    return [u.to_admin_dict() for u in users]


def create_user_admin(
    *,
    username: str,
    email: str,
    password: str,
    role: str,
) -> int:
    """
    Crea un usuario con su perfil por defecto.

    Args:
        username: nombre de usuario único.
        email: email único.
        password: contraseña en texto plano.
        role: rol ("admin" o "usuario").

    Returns:
        ID del usuario creado.

    Raises:
        ValueError: si username o email ya existen.
    """
    username_n = _normalize_username(username)
    email_n = _normalize_email(email)

    duplicated = User.query.filter(
        or_(User.username == username_n, User.email == email_n)
    ).first()
    if duplicated:
        raise ValueError("Username o email ya está en uso.")

    user = User(
        username=username_n,
        email=email_n,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()

    _ensure_profile(user)
    db.session.commit()
    return user.id


def update_user_admin(
    user_id: int,
    *,
    username: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> None:
    """
    Actualiza datos administrativos de un usuario.

    Args:
        user_id: ID de usuario a modificar.
        username: nuevo username opcional.
        email: nuevo email opcional.
        password: nueva contraseña opcional.
        role: nuevo rol opcional.
        is_active: estado activo opcional.

    Raises:
        ValueError: si el usuario no existe o hay colisión de uniques.
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError("Usuario no encontrado.")

    if username is not None:
        username_n = _normalize_username(username)
        duplicated = User.query.filter(
            User.username == username_n, User.id != user_id
        ).first()
        if duplicated:
            raise ValueError("El username ya está en uso.")
        user.username = username_n

    if email is not None:
        email_n = _normalize_email(email)
        duplicated = User.query.filter(User.email == email_n, User.id != user_id).first()
        if duplicated:
            raise ValueError("El email ya está en uso.")
        user.email = email_n

    if password is not None:
        user.password_hash = hash_password(password)

    if role is not None:
        user.role = role

    if is_active is not None:
        user.is_active = is_active

    _ensure_profile(user)
    db.session.add(user)
    db.session.commit()


def deactivate_user_admin(user_id: int) -> None:
    """
    Soft delete de usuario (is_active=False).

    Args:
        user_id: ID de usuario a desactivar.

    Raises:
        ValueError: si el usuario no existe.
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError("Usuario no encontrado.")
    user.is_active = False
    db.session.add(user)
    db.session.commit()


def ensure_dev_admin_seed() -> None:
    """
    Crea usuario admin por defecto en desarrollo si no existe.

    Crea: admin / admin con email admin@local.
    """
    existing = User.query.filter_by(username="admin").first()
    if existing:
        _ensure_profile(existing)
        db.session.commit()
        return
    user = User(
        username="admin",
        email="admin@local",
        password_hash=hash_password("admin"),
        role="admin",
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    _ensure_profile(user)
    db.session.commit()

