from __future__ import annotations

from datetime import date
from typing import Optional

from app.domains.indicadores.schemas.pendientes_out import IndicadoresPendientesOut
from app.domains.indicadores.services.indicadores_pendientes_queries import (
    aggregate_pendientes_stock,
)
from app.domains.indicadores.utils.indicadores_perf_log import PerfTimer, log_indicadores_query


def build_indicadores_pendientes(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> IndicadoresPendientesOut:
    """
    Bloque pendientes: stock actual de cola planificable por tipo de iniciador (geo OK).

    Parámetros:
        desde, hasta: ignorados (contrato común de indicadores); pendientes no depende del período.
        distrito_id: filtro opcional por domicilio efectivo con geocode OK.
        inspector_id: ignorado; la cola no tiene inspector asignado de forma confiable.

    Retorno:
        KPIs por tipo y ranking de distritos con pendientes visibles.

    Notas:
        Pendientes representa stock actual; no se filtra por período.
        ``pendientes_geolocalizacion`` y ``denuncias_pendientes`` se mantienen en el contrato JSON.
    """
    _ = (desde, hasta, inspector_id)

    timer = PerfTimer()
    agg = aggregate_pendientes_stock(distrito_id=distrito_id)
    log_indicadores_query(
        "pendientes.stock_aggregate",
        timer.elapsed_ms(),
        count=agg.mapped_count,
        scanned=agg.scanned_count,
    )

    return IndicadoresPendientesOut(
        kpis=agg.kpis,
        distritos_con_mas_pendientes=agg.distritos,
    )
