from __future__ import annotations

from datetime import date
from typing import Optional

from app.domains.indicadores.schemas.productividad_out import IndicadoresProductividadOut
from app.domains.indicadores.services.indicadores_productividad_queries import (
    query_actas_por_inspector,
    query_inspectores_no_realizadas,
    query_inspectores_realizadas,
)
from app.domains.indicadores.utils.indicadores_perf_log import PerfTimer, log_indicadores_query


def build_indicadores_productividad(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> IndicadoresProductividadOut:
    """
    Bloque productividad por inspector: realizadas, no realizadas y actas labradas.

    Parámetros:
        desde, hasta: rango (cierre de ruta para visitas; fecha actuación para actas).
        distrito_id, inspector_id: filtros opcionales.

    Retorno:
        Tres tablas ordenadas por totales descendentes.
    """
    timer = PerfTimer()
    realizadas = query_inspectores_realizadas(
        desde, hasta, distrito_id, inspector_id
    )
    log_indicadores_query("productividad.realizadas", timer.elapsed_ms())

    timer.reset()
    no_realizadas = query_inspectores_no_realizadas(
        desde, hasta, distrito_id, inspector_id
    )
    log_indicadores_query("productividad.no_realizadas", timer.elapsed_ms())

    timer.reset()
    actas = query_actas_por_inspector(desde, hasta, distrito_id, inspector_id)
    log_indicadores_query("productividad.actas_por_inspector", timer.elapsed_ms())

    return IndicadoresProductividadOut(
        inspectores_realizadas=realizadas,
        inspectores_no_realizadas=no_realizadas,
        actas_por_inspector=actas,
    )
