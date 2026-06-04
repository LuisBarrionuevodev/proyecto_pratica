from __future__ import annotations

from datetime import date
from typing import Optional

from app.domains.indicadores.schemas.no_realizadas_out import (
    ContraproducenciaCantidadItem,
    DistritoNoRealizadasItem,
    IndicadoresNoRealizadasOut,
)
from app.domains.indicadores.services.indicadores_no_realizadas_queries import (
    query_distritos_con_mas_no_realizadas,
    query_no_realizadas_por_tipo,
    query_top_contraproducencias_no_realizadas,
)


def build_indicadores_no_realizadas(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> IndicadoresNoRealizadasOut:
    """
    Bloque no realizadas: cierres con visita no realizada (contraproducencia real, sin NO_HUBO).

    Parámetros:
        desde, hasta: rango sobre fecha de cierre de ruta (``ejecutado_at`` o fecha de ruta).
        distrito_id, inspector_id: filtros opcionales.

    Retorno:
        Desglose por tipo de iniciador, top contraproducencias y distritos con más casos.
    """
    por_tipo = query_no_realizadas_por_tipo(
        desde, hasta, distrito_id, inspector_id
    )
    top_rows = query_top_contraproducencias_no_realizadas(
        desde, hasta, distrito_id, inspector_id
    )
    top_contraproducencias = [
        ContraproducenciaCantidadItem(contraproducencia=label, cantidad=cnt)
        for label, cnt in top_rows
    ]
    distrito_rows = query_distritos_con_mas_no_realizadas(
        desde, hasta, distrito_id, inspector_id
    )
    distritos_con_mas_no_realizadas = [
        DistritoNoRealizadasItem(
            distrito_id=did,
            distrito_codigo=codigo,
            distrito_nombre=nombre,
            cantidad=cnt,
        )
        for did, codigo, nombre, cnt in distrito_rows
    ]

    return IndicadoresNoRealizadasOut(
        por_tipo=por_tipo,
        top_contraproducencias=top_contraproducencias,
        distritos_con_mas_no_realizadas=distritos_con_mas_no_realizadas,
    )
