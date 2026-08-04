from __future__ import annotations

from pydantic import BaseModel, Field

from app.domains.indicadores.schemas.resumen_out import ActasPorTipo


class IndicadoresPeriodo(BaseModel):
    """Rango de fechas aplicado al bloque (ISO date)."""

    desde: str
    hasta: str


class EjecutivoKpis(BaseModel):
    """
    KPIs del resumen ejecutivo (solo visitas/actas alineadas a criterios del bloque).

    ``actuaciones_realizadas``: cierres REALIZADO en ruta PUBLICADA (mapa operativo).
    ``actas_labradas`` y desglose: actas propias en actuaciones del periodo por ``fecha``.
    """

    actuaciones_realizadas: int = Field(ge=0)
    actas_labradas: int = Field(ge=0)
    reinspecciones_notificacion_realizadas: int = Field(ge=0)
    reinspecciones_oficio_realizadas: int = Field(ge=0)
    ratificaciones_clausura_realizadas: int = Field(ge=0)
    ratificaciones_decomiso_realizadas: int = Field(ge=0)
    verificar_informar_realizadas: int = Field(ge=0)
    mercaderia_decomisada_kg: float = Field(ge=0)


class IndicadoresEjecutivoOut(BaseModel):
    """Respuesta JSON de GET /api/indicadores/ejecutivo."""

    periodo: IndicadoresPeriodo
    kpis: EjecutivoKpis
    actas_por_tipo: ActasPorTipo

    def to_json_response(self) -> dict:
        return self.model_dump(mode="json")
