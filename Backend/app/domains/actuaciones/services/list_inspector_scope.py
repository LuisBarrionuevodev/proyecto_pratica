from __future__ import annotations

from app.domains.usuarios.security.inspector_scope_policy import resolve_effective_inspector_id


def resolve_actuaciones_list_inspector_id(requested_inspector_id: int | None) -> int | None:
    """
    Adaptador de listado: aplica política de scope antes de ``ActuacionesListFilters``.

    Parámetros:
        requested_inspector_id: ``inspector_id`` de query ya convertido a int o None.

    Retorno:
        Inspector efectivo para el filtro de listado.

    Errores:
        InspectorScopeError: reglas de sesión / acceso cruzado.
    """
    return resolve_effective_inspector_id(requested_inspector_id)
