"""
Compat package para imports históricos.

La implementación real de Actuaciones vive en `app.domains.actuaciones.*`.
Este módulo re-exporta las funciones públicas para no romper imports existentes.
"""

from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.actuaciones.services.delete_service import eliminar_actuacion
from app.domains.actuaciones.services.previas_service import resolver_previas
from app.domains.actuaciones.services.update_service import actualizar_actuacion

__all__ = [
    "actualizar_actuacion",
    "crear_actuacion_desde_payload",
    "eliminar_actuacion",
    "resolver_previas",
]
