from __future__ import annotations

from flask_jwt_extended import create_access_token

from app.database import db
from app.models.profile import Profile
from app.models.user import User
from app.domains.usuarios.security.passwords import verify_password
from app.domains.usuarios.services.users_service import _ensure_profile


def login_user(*, username: str, password: str) -> dict:
    """
    Autentica un usuario por username + password.

    Args:
        username: nombre de usuario.
        password: contraseña en texto plano.

    Returns:
        Payload de login con access_token, user y profile.

    Raises:
        ValueError: si credenciales inválidas o usuario inactivo.
    """
    username_n = username.strip()
    user = User.query.filter_by(username=username_n).first()
    if not user or not verify_password(user.password_hash, password):
        raise ValueError("Credenciales inválidas.")
    if not user.is_active:
        raise ValueError("Usuario desactivado.")

    profile: Profile = _ensure_profile(user)
    db.session.commit()
    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )
    return {
        "access_token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        },
        "profile": profile.to_dict(),
    }

