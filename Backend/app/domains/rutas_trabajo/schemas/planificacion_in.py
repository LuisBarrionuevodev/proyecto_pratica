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

TipoUrgenteLiteral = Literal["DENUNCIA", "NOTIFICACION", "OFICIO"]


class PlanificacionMetricasQuery(BaseModel):
    """M1: métricas globales o acotadas a un distrito."""

    distrito_id: Optional[int] = Field(default=None, ge=1)


class PlanificacionUrgentesQuery(BaseModel):
    """M3: paginación de bandeja urgentes."""

    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)
    distrito_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="Mismo acote territorial que M1 cuando el mapa tiene distrito activo.",
    )
    tipo_urgente: Optional[TipoUrgenteLiteral] = Field(default=None)
    q: Optional[str] = Field(default=None, max_length=200)
    numero_oficio: Optional[str] = Field(default=None, max_length=60)
    numero_comprobacion: Optional[str] = Field(default=None, max_length=20)
    q_identificador: Optional[str] = Field(default=None, max_length=60)
    q_domicilio: Optional[str] = Field(default=None, max_length=200)
    rubro_id: Optional[int] = Field(default=None, ge=1)

    @field_validator("q", "numero_oficio", "numero_comprobacion", "q_identificador", "q_domicilio")
    @classmethod
    def normalize_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None

    @field_validator("tipo_urgente", mode="before")
    @classmethod
    def normalize_tipo_urgente(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        s = str(v).strip().upper()
        if s in ("TODOS", "ALL", "__ALL__"):
            return None
        return s or None


PlanificacionOrdenLiteral = Literal["prioridad", "fecha_asc", "fecha_desc", "prioridad_asc"]
PlanificacionFieldsLiteral = Literal["full", "minimal"]


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
    # Listado paginado (25) + carga mapa planificación (hasta 500 filas con coords en un solo request).
    per_page: int = Field(default=25, ge=1, le=500)
    orden: PlanificacionOrdenLiteral = Field(default="prioridad")
    fields: PlanificacionFieldsLiteral = Field(
        default="full",
        description="minimal: payload liviano para pins de mapa; full: tabla/lista.",
    )

    @field_validator("fields", mode="before")
    @classmethod
    def normalize_fields(cls, v: object) -> str:
        if v is None or v == "":
            return "full"
        s = str(v).strip().lower()
        return s if s in ("full", "minimal") else "full"

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
