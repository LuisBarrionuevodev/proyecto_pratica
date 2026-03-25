from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator


class CompletarTrabajoPendientesListFilters(BaseModel):
    """
    Query params para listar trabajos pendientes de completar (PR1: solo lectura).

    Parámetros:
        fecha: día operativo de la ruta (`RutaTrabajo.fecha`), misma que elegís al armar la ruta.
        page: página (>= 1).
        per_page: tamaño de página (1–50).
    """

    fecha: date
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=50)

    @field_validator("fecha", mode="before")
    @classmethod
    def parse_fecha(cls, v: object) -> object:
        if isinstance(v, str) and v.strip():
            return date.fromisoformat(v.strip())
        return v
