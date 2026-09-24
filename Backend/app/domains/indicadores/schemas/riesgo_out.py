from __future__ import annotations

from pydantic import BaseModel, Field


class RubroCantidadItem(BaseModel):
    rubro: str
    cantidad: int = Field(ge=0)


class MotivoCantidadItem(BaseModel):
    motivo: str
    cantidad: int = Field(ge=0)


class DecomisoKgRubroItem(BaseModel):
    rubro: str
    kg: float = Field(ge=0)


class IndicadoresRiesgoOut(BaseModel):
    """
    Respuesta JSON de GET /api/indicadores/riesgo.

    Listas vacías si no hay datos en el periodo/filtros (sin error).
    """

    top_rubros: list[RubroCantidadItem]
    top_motivos_notificacion: list[MotivoCantidadItem]
    top_motivos_comprobacion: list[MotivoCantidadItem]
    decomiso_kg_por_rubro: list[DecomisoKgRubroItem]

    def to_json_response(self) -> dict:
        return self.model_dump(mode="json")
