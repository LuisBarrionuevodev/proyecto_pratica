from __future__ import annotations

from app.domains.usuarios.services.inspector_link_service import resolve_inspector_nombre
from app.models.user import User


def user_to_auth_payload(user: User) -> dict:
    """
    Serializa usuario autenticado para login y /api/profile/me.

    Incluye vínculo operativo Inspector cuando existe.
    """
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "inspector_id": user.inspector_id,
        "inspector_nombre": resolve_inspector_nombre(user),
    }
