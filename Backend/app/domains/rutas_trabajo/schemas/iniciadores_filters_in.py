from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


TipoIniciadorLiteral = Literal[
    "RELEVAMIENTO",
    "DENUNCIA",
    "REINSPECCION_OFICIO",
    "REINSPECCION_NOTIFICACION",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
]

TurnoLiteral = Literal["MANIANA", "TARDE"]

PrioridadCategoriaLiteral = Literal["BAJA", "MEDIA", "ALTA"]


class IniciadoresPendientesFiltersIn(BaseModel):
    """
    Filtros y paginación para listar iniciadores planificables.
    """

    tipo: Optional[TipoIniciadorLiteral] = None
    prioridad: Optional[int] = Field(default=None, ge=1, le=32767)
    prioridad_categoria: Optional[PrioridadCategoriaLiteral] = None
    distrito: Optional[int] = Field(default=None, ge=1)
    calle_catalogo_id: Optional[int] = Field(default=None, ge=1)
    q: Optional[str] = Field(default=None, max_length=200)
    turno_sugerido: Optional[TurnoLiteral] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)

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
        """
        Normaliza tipo de iniciador para admitir entrada en minúsculas/mixta.
        """
        if v is None:
            return None
        return str(v).strip().upper() or None

    @field_validator("turno_sugerido", mode="before")
    @classmethod
    def normalize_turno(cls, v: Optional[str]) -> Optional[str]:
        """
        Normaliza turno sugerido para evitar fallas por casing del cliente.
        """
        if v is None:
            return None
        return str(v).strip().upper() or None

    @field_validator("prioridad_categoria", mode="before")
    @classmethod
    def normalize_prioridad_categoria(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return str(v).strip().upper() or None