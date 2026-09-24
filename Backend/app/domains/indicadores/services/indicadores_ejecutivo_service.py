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
from app.domains.indicadores.services.indicadores_operativos_queries import (
    actuacion_ids_realizadas_subquery,
    count_cierres_realizados,
    sum_visitas_oficio_realizadas,
    visitas_realizadas_por_tipo_iniciador,
)
from app.domains.indicadores.services.indicadores_productividad_queries import (
    count_visitas_realizadas_productividad_bucket,
)
from app.domains.indicadores.services.indicadores_resumen_service import (
    _count_actas_labradas,
    _float_kg,
)
from app.models import Decomiso


def build_indicadores_ejecutivo(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> IndicadoresEjecutivoOut:
    """
    Bloque ejecutivo del dashboard: cierres realizados + actas labradas alineadas.

    Criterio «realizada»: ruta PUBLICADA con ``RutaTrabajo.fecha`` en rango,
    ``RutaItem`` FINALIZADO + REALIZADO con ``actuacion_id``.
    Actas y kg se restringen a esas actuaciones (no ``Actuaciones.fecha`` ni ``ejecutado_at``).

    Parámetros:
        desde, hasta: rango inclusive.
        distrito_id, inspector_id: filtros opcionales.

    Retorno:
        ``IndicadoresEjecutivoOut`` listo para JSON.
    """
    realizadas = count_cierres_realizados(
        desde, hasta, distrito_id, inspector_id
    )
    por_tipo_ini = visitas_realizadas_por_tipo_iniciador(
        desde, hasta, distrito_id, inspector_id
    )

    sq = actuacion_ids_realizadas_subquery(desde, hasta, distrito_id, inspector_id)
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
            inspecciones_realizadas=count_visitas_realizadas_productividad_bucket(
                desde,
                hasta,
                distrito_id,
                inspector_id,
                bucket="inspecciones",
            ),
            reinspecciones_notificacion_realizadas=int(
                por_tipo_ini.get("REINSPECCION_NOTIFICACION", 0)
            ),
            reinspecciones_oficio_realizadas=int(sum_visitas_oficio_realizadas(por_tipo_ini)),
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
