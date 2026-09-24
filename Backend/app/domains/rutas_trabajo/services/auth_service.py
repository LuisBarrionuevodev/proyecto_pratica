from __future__ import annotations

from flask_jwt_extended import get_jwt_identity

from app.models import User


def get_current_user_id() -> int:
    """
    Resuelve el usuario autenticado desde JWT para auditoría (strict).

    El subject emitido en login es ``str(user.id)`` (ver ``login_user``).

    Retorna:
        int: id del usuario activo autenticado.

    Errores:
        ValueError: identidad ausente, inválida, usuario inexistente o inactivo.
    """
    try:
        identity = get_jwt_identity()
    except RuntimeError:
        raise ValueError("Usuario no autorizado.")
    except Exception:
        raise ValueError("Usuario no autorizado.")

    if identity is None:
        raise ValueError("Usuario no autorizado.")

    user_id = identity.get("user_id") if isinstance(identity, dict) else identity
    try:
        parsed_id = int(str(user_id).strip())
    except (TypeError, ValueError):
        raise ValueError("Usuario no autorizado.")

    user = User.query.get(parsed_id)
    if not user or not getattr(user, "is_active", True):
        raise ValueError("Usuario no autorizado.")
    return parsed_id


def resolve_actor_user_id(actor_user_id: int | None = None) -> int:
    """
    Resuelve actor para operaciones auditables.

    Si se provee ``actor_user_id``, lo valida.
    Si no, exige JWT válido (strict). Nunca usa primer usuario activo.
    """
    if actor_user_id is not None:
        return validate_actor_user_id(actor_user_id)
    return get_current_user_id()


def validate_actor_user_id(actor_user_id: int) -> int:
    """
    Valida un actor explícito para operaciones internas/CLI (sin JWT).

    Parámetros:
        actor_user_id: id de usuario que ejecuta la operación auditable.

    Retorna:
        int: id validado.

    Errores:
        ValueError: id inválido, usuario inexistente o inactivo.
    """
    try:
        parsed_id = int(actor_user_id)
    except (TypeError, ValueError):
        raise ValueError("actor_user_id inválido.")
    if parsed_id < 1:
        raise ValueError("actor_user_id inválido.")

    user = User.query.get(parsed_id)
    if not user or not getattr(user, "is_active", True):
        raise ValueError("actor_user_id no corresponde a un usuario activo.")
    return parsed_id
