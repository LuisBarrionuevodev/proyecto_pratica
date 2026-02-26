from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models.user import User


def _resolve_user_from_identity() -> User | None:
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        user_id = identity.get("user_id")
    else:
        user_id = identity
    if user_id is None:
        return None
    try:
        return User.query.get(int(user_id))
    except (TypeError, ValueError):
        return None


def require_role(role: str) -> Callable:
    """
    Restringe acceso al endpoint a usuarios autenticados de un rol.

    Args:
        role: rol requerido (por ejemplo, "admin").

    Returns:
        Decorador para función de ruta Flask.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        @jwt_required()
        def wrapper(*args: Any, **kwargs: Any):
            user = _resolve_user_from_identity()
            if not user or not user.is_active:
                return jsonify({"detail": "No autorizado"}), 401
            if user.role != role:
                return jsonify({"detail": "No tiene permisos para esta acción"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator

