"""Scope de inspector para endpoints GET /map/operativo/*."""

from __future__ import annotations

from flask import jsonify

from app.domains.usuarios.security.decorators import resolve_user_from_identity
from app.domains.usuarios.security.inspector_scope_policy import (
    InspectorScopeError,
    resolve_effective_inspector_id,
)
from app.domains.usuarios.services.inspector_link_service import INSPECTOR_ROLE


def resolve_map_operativo_inspector_scope(
    inspector_id_raw: str | None,
) -> tuple[int | None, bool, tuple | None]:
    """
    Resuelve ``inspector_id`` efectivo y si aplica modo solo ítems de ruta (Inspector).

    Parámetros:
        inspector_id_raw: valor crudo de query ``inspector_id``.

    Retorno:
        Tupla (inspector_id efectivo, solo_items_ruta_inspector, error_response).
        ``error_response`` es (body, status) si falla la política de scope.

    Errores:
        InspectorScopeError → 401/403 en la tercera posición de la tupla.
    """
    user = resolve_user_from_identity()
    requested: int | None = None
    if inspector_id_raw not in (None, ""):
        try:
            requested = int(inspector_id_raw)
        except (TypeError, ValueError):
            return None, False, (jsonify({"detail": "inspector_id inválido."}), 400)

    try:
        effective = resolve_effective_inspector_id(requested, user=user)
    except InspectorScopeError as exc:
        return None, False, (jsonify({"detail": str(exc)}), exc.status_code)

    solo_ruta = bool(user and user.role == INSPECTOR_ROLE)
    return effective, solo_ruta, None
