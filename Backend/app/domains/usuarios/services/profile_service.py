from __future__ import annotations

from flask_jwt_extended import get_jwt_identity

from app.database import db
from app.domains.usuarios.security.passwords import hash_password, verify_password
from app.domains.usuarios.services.users_service import _ensure_profile
from app.models.user import User


def _get_current_user() -> User:
    identity = get_jwt_identity()
    user_id = identity.get("user_id") if isinstance(identity, dict) else identity
    try:
        parsed_id = int(user_id)
    except (TypeError, ValueError):
        raise ValueError("Usuario no autorizado.")
    user = User.query.get(parsed_id)
    if not user or not user.is_active:
        raise ValueError("Usuario no autorizado.")
    return user


def get_my_profile() -> dict:
    """
    Retorna user + profile del usuario autenticado.

    Returns:
        Dict con datos de usuario y perfil.

    Raises:
        ValueError: si el usuario no existe o está inactivo.
    """
    user = _get_current_user()
    profile = _ensure_profile(user)
    db.session.commit()
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        },
        "profile": profile.to_dict(),
    }


def update_my_profile(*, nickname: str | None = None, avatar_key: str | None = None) -> dict:
    """
    Actualiza nickname/avatar del perfil autenticado.

    Args:
        nickname: nuevo nickname opcional.
        avatar_key: nueva clave de avatar opcional.

    Returns:
        Perfil actualizado serializado.

    Raises:
        ValueError: si el usuario no existe o está inactivo.
    """
    user = _get_current_user()
    profile = _ensure_profile(user)
    if nickname is not None:
        profile.nickname = nickname
    if avatar_key is not None:
        profile.avatar_key = avatar_key
    db.session.add(profile)
    db.session.commit()
    return profile.to_dict()


def change_my_password(*, current_password: str, new_password: str) -> None:
    """
    Cambia contraseña del usuario autenticado validando la actual.

    Args:
        current_password: contraseña actual.
        new_password: nueva contraseña.

    Raises:
        ValueError: si la contraseña actual no coincide.
    """
    user = _get_current_user()
    if not verify_password(user.password_hash, current_password):
        raise ValueError("La contraseña actual es incorrecta.")
    user.password_hash = hash_password(new_password)
    db.session.add(user)
    db.session.commit()

