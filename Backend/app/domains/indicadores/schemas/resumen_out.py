from __future__ import annotations

from pydantic import BaseModel, Field


class ContraproducenciaTopItem(BaseModel):
    """Un valor de contraproducencia y su frecuencia en el conjunto filtrado."""

    valor: str
    count: int = Field(ge=0)


class ActuacionesResumen(BaseModel):
    total: int = Field(ge=0)
    con_contraproducencia: int = Field(ge=0)
    sin_contraproducencia: int = Field(ge=0)


class ActasPorTipo(BaseModel):
    inspeccion: int = Field(ge=0)
    notificacion: int = Field(ge=0)
    comprobacion: int = Field(ge=0)
    clausura: int = Field(ge=0)
    decomiso: int = Field(ge=0)


class DecomisoKgPorMesItem(BaseModel):
    """Kilos decomisados agregados por año-mes de la fecha de actuación."""

    anio: int
    mes: int = Field(ge=1, le=12)
    kg: float = Field(ge=0)


class DecomisoKgResumen(BaseModel):
    """Total kg decomisados en el conjunto filtrado y serie simple por mes (fecha actuación)."""

    total_kg: float = Field(ge=0)
    por_mes: list[DecomisoKgPorMesItem]


class RubroTopItem(BaseModel):
    """Rubro con cantidad de actuaciones en el conjunto filtrado (solo actuación con domicilio y rubro)."""

    rubro_id: int
    nombre: str
    count: int = Field(ge=0)


class RutaItemsEjecucionResumen(BaseModel):
    """
    Conteos de ítems de ruta por fecha de ruta (no filtrados por distrito/inspector).

    Útil como vista global del periodo; no se cruza con los filtros de actuación.
    """

    total: int = Field(ge=0)
    estado_ejecucion_realizado: int = Field(ge=0)
    estado_ejecucion_no_realizado: int = Field(ge=0)
    estado_ejecucion_sin_clasificar: int = Field(ge=0)


class IndicadoresResumenOut(BaseModel):
    """Respuesta JSON del dashboard operativo (v1)."""

    periodo: dict
    filtros: dict
    actuaciones: ActuacionesResumen
    contraproducencias_top: list[ContraproducenciaTopItem]
    actas_por_tipo: ActasPorTipo
    ruta_items_ejecucion: RutaItemsEjecucionResumen
    top_rubros: list[RubroTopItem]
    decomiso_kg: DecomisoKgResumen

    def to_json_response(self) -> dict:
        """Serialización estable para Flask jsonify."""
        return self.model_dump(mode="json")
