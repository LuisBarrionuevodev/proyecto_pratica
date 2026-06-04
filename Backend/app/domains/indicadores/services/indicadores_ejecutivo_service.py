from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import func

from app.database import db
from app.domains.indicadores.schemas.ejecutivo_out import (
    EjecutivoKpis,
    IndicadoresEjecutivoOut,
    IndicadoresPeriodo,
)
from app.domains.indicadores.services.indicadores_resumen_service import (
    _actuacion_ids_subquery,
    _count_actas_labradas,
    _float_kg,
    count_actuaciones_realizadas_visita,
    visitas_realizadas_por_tipo_iniciador,
)
from app.models import Decomiso


def build_indicadores_ejecutivo(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> IndicadoresEjecutivoOut:
    """
    Bloque ejecutivo del dashboard: realizadas (mapa) + actas labradas (fecha actuación).

    Parámetros:
        desde, hasta: rango inclusive.
        distrito_id, inspector_id: filtros opcionales.

    Retorno:
        ``IndicadoresEjecutivoOut`` listo para JSON.
    """
    realizadas = count_actuaciones_realizadas_visita(
        desde, hasta, distrito_id, inspector_id
    )
    por_tipo_ini = visitas_realizadas_por_tipo_iniciador(
        desde, hasta, distrito_id, inspector_id
    )

    sq = _actuacion_ids_subquery(desde, hasta, distrito_id, inspector_id)
    actas_por_tipo = _count_actas_labradas(sq)
    actas_labradas = (
        actas_por_tipo.inspeccion
        + actas_por_tipo.notificacion
        + actas_por_tipo.comprobacion
        + actas_por_tipo.clausura
        + actas_por_tipo.decomiso
    )

    sum_kg = (
        db.session.query(func.sum(Decomiso.cantidad))
        .join(sq, sq.c.id == Decomiso.actuacion_id)
        .scalar()
    )

    return IndicadoresEjecutivoOut(
        periodo=IndicadoresPeriodo(desde=desde.isoformat(), hasta=hasta.isoformat()),
        kpis=EjecutivoKpis(
            actuaciones_realizadas=int(realizadas),
            actas_labradas=int(actas_labradas),
            reinspecciones_notificacion_realizadas=int(
                por_tipo_ini.get("REINSPECCION_NOTIFICACION", 0)
            ),
            ratificaciones_clausura_realizadas=int(
                por_tipo_ini.get("RATIFICACION_CLAUSURA_OFICIO", 0)
            ),
            ratificaciones_decomiso_realizadas=int(
                por_tipo_ini.get("RATIFICACION_DECOMISO_OFICIO", 0)
            ),
            verificar_informar_realizadas=int(
                por_tipo_ini.get("VERIFICAR_INFORMAR_OFICIO", 0)
            ),
            mercaderia_decomisada_kg=_float_kg(sum_kg),
        ),
        actas_por_tipo=actas_por_tipo,
    )
