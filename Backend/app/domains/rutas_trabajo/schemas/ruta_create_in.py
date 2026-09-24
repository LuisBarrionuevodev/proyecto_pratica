from __future__ import annotations

from datetime import date
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator


class RutaTrabajoCreateIn(BaseModel):
    """
    Valida la creación de una ruta de trabajo.

    Inputs:
    - fecha: fecha operativa de la ruta.
    - turno: turno del modelo actual (MANIANA|TARDE).
    - observaciones: texto libre opcional.
    """

    fecha: date
    turno: Literal["MANIANA", "TARDE"]
    observaciones: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("observaciones")
    @classmethod
    def normalize_observaciones(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None
