from __future__ import annotations

from flask_jwt_extended import get_jwt_identity

from app.models import User


def get_current_user_id_or_fallback() -> int:
    """
    Resuelve usuario autenticado para auditoría.

    Retorna:
    - user_id válido del JWT cuando existe.
    - fallback al primer usuario activo para endpoints legacy sin JWT.

    Errores:
    - ValueError: cuando no puede resolverse un usuario activo.
    """
    try:
        identity = get_jwt_identity()
    except Exception:
        identity = None

    user_id = identity.get("user_id") if isinstance(identity, dict) else identity
    if user_id is not None:
        try:
            parsed_id = int(user_id)
        except (TypeError, ValueError):
            parsed_id = None
        if parsed_id is not None:
            user = User.query.get(parsed_id)
            if user and getattr(user, "is_active", True):
                return parsed_id

    fallback_user = (
        User.query.filter(User.is_active.is_(True))
        .order_by(User.id.asc())
        .first()
    )
    if fallback_user:
        return int(fallback_user.id)
    raise ValueError("No hay usuario activo para registrar auditoría")
