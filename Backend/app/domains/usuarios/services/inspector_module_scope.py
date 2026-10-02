"""
Contrato de scope Inspector para módulos operativos (trabajos, actuaciones, indicadores, mapa).

Integraciones futuras deben obtener el id efectivo únicamente vía ``resolve_effective_inspector_id``.
"""

from __future__ import annotations

from app.domains.usuarios.security.inspector_scope_policy import (
    InspectorScopeError,
    resolve_effective_inspector_id,
)

__all__ = [
    "InspectorScopeError",
    "resolve_effective_inspector_id",
]
