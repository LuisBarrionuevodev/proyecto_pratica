from __future__ import annotations

from pydantic import BaseModel, Field


class PendientesKpis(BaseModel):
    """
    Conteos de cola planificable (iniciador PENDIENTE, geo OK) — stock actual.

    ``denuncias_pendientes`` y ``pendientes_geolocalizacion`` se mantienen por compatibilidad;
    la UI de indicadores no los muestra.
    """

    relevamientos_pendientes: int = Field(ge=0)
    reinspecciones_oficio_pendientes: int = Field(ge=0)
    reinspecciones_notificacion_pendientes: int = Field(ge=0)
    denuncias_pendientes: int = Field(ge=0)
    pendientes_geolocalizacion: int = Field(ge=0)


class DistritoPendientesItem(BaseModel):
    distrito_id: int
    distrito_codigo: str
    distrito_nombre: str
    relevamientos: int = Field(ge=0)
    denuncias: int = Field(ge=0)
    reinspecciones_oficio: int = Field(ge=0)
    reinspecciones_notificacion: int = Field(ge=0)
    sin_geolocalizacion: int = Field(ge=0)
    total: int = Field(ge=0)


class IndicadoresPendientesOut(BaseModel):
    """Respuesta JSON de GET /api/indicadores/pendientes."""

    kpis: PendientesKpis
    distritos_con_mas_pendientes: list[DistritoPendientesItem]

    def to_json_response(self) -> dict:
        return self.model_dump(mode="json")
