from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator


class RutaItemOrdenTrabajoPatchIn(BaseModel):
    """
    Valida payload para asignar/reemplazar OT en un item de ruta.
    """

    numero_orden_trabajo: str

    @field_validator("numero_orden_trabajo", mode="before")
    @classmethod
    def validate_numero_ot(cls, v: Any) -> str:
        if v is None:
            raise ValueError("numero_orden_trabajo es obligatorio")
        value = str(v).strip()
        if not value:
            raise ValueError("numero_orden_trabajo es obligatorio")
        if not value.isdigit():
            raise ValueError("numero_orden_trabajo debe ser numérico")
        return value
