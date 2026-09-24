from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class IndicadoresResumenQuery(BaseModel):
    """
    Query params para GET resumen de indicadores.

    Parámetros:
        desde: inicio del rango (inclusive), fecha operativa de ``RutaTrabajo``.
        hasta: fin del rango (inclusive), fecha operativa de ``RutaTrabajo``.
        distrito_id: filtra visitas cuyo domicilio efectivo pertenece al distrito.
        inspector_id: filtra actuaciones donde el inspector figura en la relación (no borrada).

    Errores de validación: Pydantic ValidationError si fechas inválidas o desde > hasta.
    """

    desde: date
    hasta: date
    distrito_id: Optional[int] = Field(default=None, ge=1)
    inspector_id: Optional[int] = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _rango_coherente(self) -> IndicadoresResumenQuery:
        if self.desde > self.hasta:
            raise ValueError("desde no puede ser posterior a hasta.")
        return self
