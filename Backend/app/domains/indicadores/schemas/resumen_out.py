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
    Conteos de ítems de ruta por fecha de ruta en rutas **PUBLICADAS** (sin borradores).

    Útil como vista global del periodo; no se cruza con los filtros de actuación.
    """

    total: int = Field(ge=0)
    estado_ejecucion_realizado: int = Field(ge=0)
    estado_ejecucion_no_realizado: int = Field(ge=0)
    estado_ejecucion_sin_clasificar: int = Field(ge=0)


class ActasLabradasMesItem(BaseModel):
    """Actas efectivamente labradas en actuaciones del mes (sin previas/origen)."""

    anio: int
    mes: int = Field(ge=1, le=12)
    total: int = Field(ge=0)
    inspeccion: int = Field(ge=0)
    notificacion: int = Field(ge=0)
    comprobacion: int = Field(ge=0)
    clausura: int = Field(ge=0)
    decomiso: int = Field(ge=0)


class RankingInspectorItem(BaseModel):
    inspector_id: int
    inspector_nombre: str
    total_actuaciones: int = Field(ge=0)


class ReinspeccionesRealizadas(BaseModel):
    """Reinspecciones cerradas con visita realizada (ruta publicada, actuación vinculada)."""

    notificacion: int = Field(ge=0)
    oficio: int = Field(ge=0)


class ContraproducenciaPorTipoItem(BaseModel):
    """Agrupación por valor de contraproducencia (incluye bucket sin contraproducencia)."""

    valor: str
    count: int = Field(ge=0)


class ActuacionPorTipoOperativoItem(BaseModel):
    tipo: str
    count: int = Field(ge=0)


class MapaOperativoResumen(BaseModel):
    """
    Conteos alineados al mapa operativo D1 (mismo criterio que ``/map/operativo/*``).

    ``pendientes_total`` = cola planificable + EN_PROCESO en ruta publicada (geocode OK).
    ``realizados_visita`` = ítems finalizados con ejecución REALIZADO en ruta publicada (fecha de cierre en rango).
    """

    pendientes_cola: int = Field(ge=0)
    pendientes_completar_trabajo: int = Field(ge=0)
    pendientes_total: int = Field(ge=0)
    realizados_visita: int = Field(ge=0)


class IndicadoresResumenOut(BaseModel):
    """Respuesta JSON del dashboard operativo (v1)."""

    periodo: dict
    filtros: dict
    actuaciones: ActuacionesResumen
    contraproducencias_top: list[ContraproducenciaTopItem]
    actas_por_tipo: ActasPorTipo
    actas_labradas_mensual: list[ActasLabradasMesItem]
    ranking_inspectores: list[RankingInspectorItem]
    reinspecciones_realizadas: ReinspeccionesRealizadas
    contraproducencias_por_tipo: list[ContraproducenciaPorTipoItem]
    actuaciones_por_tipo_operativo: list[ActuacionPorTipoOperativoItem]
    ruta_items_ejecucion: RutaItemsEjecucionResumen
    mapa_operativo: MapaOperativoResumen
    top_rubros: list[RubroTopItem]
    decomiso_kg: DecomisoKgResumen

    def to_json_response(self) -> dict:
        """Serialización estable para Flask jsonify."""
        return self.model_dump(mode="json")
