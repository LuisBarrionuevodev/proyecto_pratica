from __future__ import annotations

from datetime import date
from typing import Optional

from app.domains.indicadores.schemas.riesgo_out import (
    DecomisoKgRubroItem,
    IndicadoresRiesgoOut,
    MotivoCantidadItem,
    RubroCantidadItem,
)
from app.domains.indicadores.services.indicadores_resumen_service import (
    query_decomiso_kg_por_rubro,
    query_top_motivos_comprobacion,
    query_top_motivos_notificacion,
    query_top_rubros_actuaciones,
)


def build_indicadores_riesgo(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> IndicadoresRiesgoOut:
    """
    Bloque riesgo bromatológico.

    Parámetros:
        desde, hasta, distrito_id, inspector_id: filtros sobre actuaciones del periodo.

    Retorno:
        Rankings de rubros, motivos (notificación/comprobación) y kg decomisados por rubro.
    """
    rubro_rows = query_top_rubros_actuaciones(
        desde, hasta, distrito_id, inspector_id
    )
    top_rubros = [
        RubroCantidadItem(rubro=nombre, cantidad=cnt) for _rid, nombre, cnt in rubro_rows
    ]

    notif_rows = query_top_motivos_notificacion(
        desde, hasta, distrito_id, inspector_id
    )
    top_motivos_notificacion = [
        MotivoCantidadItem(motivo=nombre, cantidad=cnt) for nombre, cnt in notif_rows
    ]

    comp_rows = query_top_motivos_comprobacion(
        desde, hasta, distrito_id, inspector_id
    )
    top_motivos_comprobacion = [
        MotivoCantidadItem(motivo=nombre, cantidad=cnt) for nombre, cnt in comp_rows
    ]

    decomiso_rows = query_decomiso_kg_por_rubro(
        desde, hasta, distrito_id, inspector_id
    )
    decomiso_kg_por_rubro = [
        DecomisoKgRubroItem(rubro=nombre, kg=kg) for nombre, kg in decomiso_rows
    ]

    return IndicadoresRiesgoOut(
        top_rubros=top_rubros,
        top_motivos_notificacion=top_motivos_notificacion,
        top_motivos_comprobacion=top_motivos_comprobacion,
        decomiso_kg_por_rubro=decomiso_kg_por_rubro,
    )
