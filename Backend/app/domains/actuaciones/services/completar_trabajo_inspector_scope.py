from __future__ import annotations

from app.domains.usuarios.security.decorators import resolve_user_from_identity
from app.domains.usuarios.security.inspector_scope_policy import (
    InspectorScopeError,
    resolve_effective_inspector_id,
)


def resolve_completar_trabajo_effective_inspector_id() -> int | None:
    """
    Inspector efectivo para listado/resumen Completar trabajo (sin query param).

    Parámetros:
        Ninguno; usa JWT de la request.

    Retorno:
        ``inspector_id`` para rol Inspector; ``None`` para admin/usuario (vista global).

    Errores:
        InspectorScopeError: 401 sin sesión; 403 contrato Inspector incumplido.
    """
    user = resolve_user_from_identity()
    if user is None:
        raise InspectorScopeError("No autorizado.", status_code=401)
    return resolve_effective_inspector_id(None, user=user)
