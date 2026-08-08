from __future__ import annotations

from datetime import date
from typing import Optional

from app.domains.indicadores.schemas.no_realizadas_out import (
    ContraproducenciaCantidadItem,
    ContraproducenciaResumenItem,
    DistritoNoRealizadasItem,
    IndicadoresNoRealizadasOut,
)
from app.domains.indicadores.services.indicadores_no_realizadas_queries import (
    query_contraproducencias_resumen_counts,
    query_distritos_con_mas_no_realizadas,
    query_no_realizadas_por_tipo,
    query_top_contraproducencias_no_realizadas,
)
from app.domains.indicadores.utils.contraproducencia_indicador_buckets import (
    BUCKET_LABELS,
    BUCKET_ORDER,
)


def build_indicadores_no_realizadas(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> IndicadoresNoRealizadasOut:
    """
    Bloque no realizadas: trabajos no realizados con contraproducencia real en el período.

    Parámetros:
        desde, hasta: rango sobre ``RutaTrabajo.fecha`` (período operativo de la ruta).
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
    total_resumen, bucket_counts = query_contraproducencias_resumen_counts(
        desde, hasta, distrito_id, inspector_id
    )
    contraproducencias_resumen = [
        ContraproducenciaResumenItem(
            bucket=key,
            label=BUCKET_LABELS[key],
            cantidad=int(bucket_counts.get(key, 0)),
        )
        for key in BUCKET_ORDER
    ]

    return IndicadoresNoRealizadasOut(
        por_tipo=por_tipo,
        top_contraproducencias=top_contraproducencias,
        distritos_con_mas_no_realizadas=distritos_con_mas_no_realizadas,
        total=total_resumen,
        contraproducencias_resumen=contraproducencias_resumen,
    )
