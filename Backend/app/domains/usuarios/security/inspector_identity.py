from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import jsonify
from flask_jwt_extended import jwt_required

from app.domains.usuarios.security.decorators import resolve_user_from_identity
from app.domains.usuarios.services.inspector_link_service import INSPECTOR_ROLE
from app.models.user import User


class InspectorIdentityError(Exception):
    """Error de contrato operativo Inspector (HTTP 401/403)."""

    def __init__(self, message: str, *, status_code: int = 403) -> None:
        super().__init__(message)
        self.status_code = status_code


def get_current_inspector_user() -> User:
    """
    Usuario autenticado que cumple contrato Inspector (rol + vínculo).

    Raises:
        InspectorIdentityError: JWT inválido, usuario inactivo, rol distinto o sin vínculo.
    """
    user = resolve_user_from_identity()
    if not user:
        raise InspectorIdentityError("No autorizado.", status_code=401)
    if not user.is_active:
        raise InspectorIdentityError("Usuario inactivo.", status_code=403)
    if user.role != INSPECTOR_ROLE:
        raise InspectorIdentityError("No tiene permisos de Inspector.", status_code=403)
    if user.inspector_id is None or user.inspector is None:
        raise InspectorIdentityError(
            "La cuenta no tiene un inspector vinculado.",
            status_code=403,
        )
    return user


def get_current_inspector_id() -> int:
    """
    ID del Inspector operativo del JWT (sin confiar en body/query).

    Returns:
        ``inspector.id`` vinculado a la cuenta autenticada.

    Raises:
        InspectorIdentityError: contrato Inspector incumplido.
    """
    user = get_current_inspector_user()
    return int(user.inspector_id)


def require_inspector_contract(fn: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorador reutilizable: exige sesión Inspector con vínculo válido.

    Responde 401/403 JSON controlado; no ejecuta el handler si falla.
    """

    @wraps(fn)
    @jwt_required()
    def wrapper(*args: Any, **kwargs: Any):
        try:
            get_current_inspector_id()
        except InspectorIdentityError as e:
            return jsonify({"detail": str(e)}), e.status_code
        return fn(*args, **kwargs)

    return wrapper
