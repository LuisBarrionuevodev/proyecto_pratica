from __future__ import annotations

from app.domains.usuarios.security.decorators import resolve_user_from_identity
from app.domains.usuarios.services.inspector_link_service import INSPECTOR_ROLE
from app.models.user import User

CROSS_INSPECTOR_ACCESS_DETAIL = "No tiene permisos para consultar otro inspector."

_USER_UNSET = object()


class InspectorScopeError(Exception):
    """Error de scope operativo por Inspector (HTTP 401/403)."""

    def __init__(self, message: str, *, status_code: int = 403) -> None:
        super().__init__(message)
        self.status_code = status_code


def resolve_effective_inspector_id(
    requested_inspector_id: int | None,
    *,
    user: User | None | object = _USER_UNSET,
) -> int | None:
    """
    Determina el ``inspector_id`` efectivo para filtros y métricas.

    El cliente no define el Inspector operativo: para rol ``relevador`` solo se
    permite el vínculo persistido en la cuenta. Admin y usuario conservan el filtro
    global solicitado (o ninguno).

    Parámetros:
        requested_inspector_id: valor de query/body ya parseado (puede ser None).
        user: usuario de sesión; si es None se resuelve desde JWT.

    Retorno:
        Id de inspector a aplicar en consultas, o ``None`` sin filtro por inspector.

    Errores:
        InspectorScopeError: 401 sin sesión; 403 inactivo, sin vínculo o acceso cruzado.
    """
    if user is _USER_UNSET:
        user = resolve_user_from_identity()
    if user is None:
        raise InspectorScopeError("No autorizado.", status_code=401)
    if not user.is_active:
        raise InspectorScopeError("Usuario inactivo.", status_code=403)

    if user.role == INSPECTOR_ROLE:
        if user.inspector_id is None or user.inspector is None:
            raise InspectorScopeError(
                "La cuenta no tiene un inspector vinculado.",
                status_code=403,
            )
        own_id = int(user.inspector_id)
        if requested_inspector_id is None:
            return own_id
        requested = int(requested_inspector_id)
        if requested != own_id:
            raise InspectorScopeError(CROSS_INSPECTOR_ACCESS_DETAIL, status_code=403)
        return own_id

    return requested_inspector_id
