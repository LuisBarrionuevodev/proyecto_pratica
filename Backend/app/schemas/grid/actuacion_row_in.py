"""
Compat shim: `app.schemas.grid.actuacion_row_in` -> `app.domains.actuaciones.schemas.grid.actuacion_row_in`.

Mantiene imports existentes (routes/pipelines/validate_service) sin tocar lógica.
"""

from app.domains.actuaciones.schemas.grid.actuacion_row_in import (  # noqa: F401
    ActuacionGridRowIn,
    ContraEnum,
    Tipo,
)

__all__ = [
    "ActuacionGridRowIn",
    "ContraEnum",
    "Tipo",
]

