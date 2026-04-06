"""
Query params / validación para endpoints de Planificación (M1, M3, M4).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.domains.rutas_trabajo.schemas.iniciadores_filters_in import (
    TipoIniciadorLiteral,
    TurnoLiteral,
    PrioridadCategoriaLiteral,
)


class PlanificacionMetricasQuery(BaseModel):
    """M1: métricas globales o acotadas a un distrito."""

    distrito_id: Optional[int] = Field(default=None, ge=1)


class PlanificacionUrgentesQuery(BaseModel):
    """M3: paginación de bandeja urgentes."""

    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)


PlanificacionOrdenLiteral = Literal["prioridad", "fecha_asc", "fecha_desc", "prioridad_asc"]


class PlanificacionPendientesContextoQuery(BaseModel):
    """
    M4: pendientes territoriales — distrito_id obligatorio.

    Mismos filtros opcionales que iniciadores-pendientes salvo distrito (fijo por param).
    """

    distrito_id: int = Field(ge=1)
    tipo: Optional[TipoIniciadorLiteral] = None
    prioridad: Optional[int] = Field(default=None, ge=1, le=32767)
    prioridad_categoria: Optional[PrioridadCategoriaLiteral] = None
    calle_catalogo_id: Optional[int] = Field(default=None, ge=1)
    q: Optional[str] = Field(default=None, max_length=200)
    turno_sugerido: Optional[TurnoLiteral] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)
    orden: PlanificacionOrdenLiteral = Field(default="prioridad")

    @field_validator("q")
    @classmethod
    def normalize_q(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None

    @field_validator("tipo", mode="before")
    @classmethod
    def normalize_tipo(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return str(v).strip().upper() or None

    @field_validator("turno_sugerido", mode="before")
    @classmethod
    def normalize_turno(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return str(v).strip().upper() or None

    @field_validator("prioridad_categoria", mode="before")
    @classmethod
    def normalize_prioridad_categoria(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return str(v).strip().upper() or None

    @field_validator("orden", mode="before")
    @classmethod
    def normalize_orden(cls, v: object) -> str:
        if v is None or v == "":
            return "prioridad"
        s = str(v).strip().lower()
        return s if s in ("prioridad", "fecha_asc", "fecha_desc", "prioridad_asc") else "prioridad"
