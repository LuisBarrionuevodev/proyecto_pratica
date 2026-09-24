from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

StatusOperativoRow = Literal[
    "sin_punto",
    "punto_dudoso",
    "error",
    "manual",
    "geolocalizado",
]

GeoChip = Literal["EN_MAPA", "SIN_COORDS"]


class GestionDomiciliosSummaryOut(BaseModel):
    """Contadores agregados para header/filtros de Gestión Domicilios."""

    total: int = 0
    requieren_accion: int = 0
    sin_punto: int = 0
    punto_dudoso: int = 0
    errores: int = 0
    manuales: int = 0
    geolocalizados: int = 0


class GestionDomiciliosRowTecnicoOut(BaseModel):
    """Campos técnicos opcionales (``include_tecnico=1``). No mostrar al operador común."""

    score_unificado: Optional[float] = None
    match_strategy: Optional[str] = None
    confidence_reason: Optional[str] = None
    nomenclatura_estado: Optional[str] = None
    geocode_estado: Optional[str] = None
    motivos: Optional[list[str]] = None


class GestionDomiciliosRowOut(BaseModel):
    """Fila paginada para tabla operativa."""

    domicilio_id: int
    domicilio_linea: str
    calle_sugerida: Optional[str] = None
    referencia_breve: Optional[str] = None
    status_operativo: StatusOperativoRow
    status_operativo_label: str
    geo_chip: GeoChip
    has_coordinates: bool
    lat: Optional[float] = None
    lng: Optional[float] = None
    requiere_accion: bool = False
    tecnico: Optional[GestionDomiciliosRowTecnicoOut] = None


class GestionDomiciliosMapPointOut(BaseModel):
    """Punto ligero para el mapa (separado de ``rows``)."""

    domicilio_id: int
    lat: float
    lng: float
    status_operativo: StatusOperativoRow
    status_operativo_label: str
    label: str
    geo_chip: GeoChip = "EN_MAPA"
    requiere_accion: bool = False


class GestionDomiciliosMapPointsMetaOut(BaseModel):
    """Metadata de ``map_points`` (límite, truncado, filtros aplicados)."""

    returned: int = Field(ge=0)
    limit: int = Field(ge=1)
    truncated: bool = False
    total_matching: int = Field(ge=0)
    map_mode: str
    bbox_applied: bool = False


class GestionDomiciliosPaginationOut(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class GestionDomiciliosResponse(BaseModel):
    """Respuesta completa GET /map/gestion-domicilios."""

    summary: GestionDomiciliosSummaryOut
    rows: list[GestionDomiciliosRowOut]
    map_points: list[GestionDomiciliosMapPointOut]
    map_points_meta: GestionDomiciliosMapPointsMetaOut | None = None
    pagination: GestionDomiciliosPaginationOut
