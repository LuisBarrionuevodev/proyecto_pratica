from __future__ import annotations

from datetime import date
from typing import Optional

from app.domains.indicadores.schemas.productividad_out import IndicadoresProductividadOut
from app.domains.indicadores.services.indicadores_productividad_queries import (
    query_actas_por_inspector,
    query_inspectores_no_realizadas,
    query_inspectores_realizadas,
)


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
    return IndicadoresProductividadOut(
        inspectores_realizadas=query_inspectores_realizadas(
            desde, hasta, distrito_id, inspector_id
        ),
        inspectores_no_realizadas=query_inspectores_no_realizadas(
            desde, hasta, distrito_id, inspector_id
        ),
        actas_por_inspector=query_actas_por_inspector(
            desde, hasta, distrito_id, inspector_id
        ),
    )
