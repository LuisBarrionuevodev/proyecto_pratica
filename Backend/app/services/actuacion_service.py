"""
Compat: re-export de services de Actuaciones.

Este módulo existe para no romper imports existentes (p.ej. en `routes/`).
La implementación real vive en `app.services.actuaciones.*_service`.
"""

from __future__ import annotations

from app.services.actuaciones.create_service import crear_actuacion_desde_payload
from app.services.actuaciones.update_service import actualizar_actuacion
from app.services.actuaciones.delete_service import eliminar_actuacion

__all__ = [
    "crear_actuacion_desde_payload",
    "actualizar_actuacion",
    "eliminar_actuacion",
]
