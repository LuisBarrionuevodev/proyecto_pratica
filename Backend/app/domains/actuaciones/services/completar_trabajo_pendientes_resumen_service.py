from __future__ import annotations

from datetime import date

from sqlalchemy import and_, case, func, or_

from app.database import db
from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    dia_resumen_completar_trabajo_pendientes,
)
from app.domains.actuaciones.services.completar_trabajo_pendiente_filters import (
    pending_archivo_exists_correlated,
)
from app.domains.actuaciones.services.completar_trabajo_pendientes_query import (
    apply_completar_trabajo_inspector_scope,
)
from app.models import RutaItem, RutaTrabajo


def list_completar_trabajo_pendientes_resumen_por_dia(
    *,
    fecha_desde: date,
    fecha_hasta: date,
    inspector_id_effective: int | None = None,
) -> tuple[list[dict], dict]:
    """
    Agrega por día operativo de ruta publicada el ámbito Completar trabajo.

    Misma base de ítems que el listado por fecha; el scope Inspector se aplica antes del GROUP BY.

    Parámetros:
        fecha_desde: inicio inclusive (`RutaTrabajo.fecha`).
        fecha_hasta: fin inclusive.
        inspector_id_effective: scope Inspector; None = vista global.

    Retorno:
        Tupla (`dias`, `meta`).
    """
    hoy = date.today()

    pending_media = pending_archivo_exists_correlated()
    fotos_pendientes_tras_cierre = and_(
        RutaItem.estado_ruta_item == "FINALIZADO",
        RutaItem.fotos_pendientes_cerradas_at.is_(None),
        or_(
            pending_media,
            RutaItem.evidencias_pendientes_abiertas.is_(True),
        ),
    )
    pendientes_expr = func.sum(
        case(
            (RutaItem.estado_ruta_item == "EN_PROCESO", 1),
            (fotos_pendientes_tras_cierre, 1),
            else_=0,
        )
    ).label("pendientes_cierre")
    items_expr = func.count(RutaItem.id).label("items_con_actuacion")

    aggregate = (
        db.session.query(
            RutaTrabajo.fecha,
            items_expr,
            pendientes_expr,
        )
        .select_from(RutaItem)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaTrabajo.estado_ruta == "PUBLICADA",
            RutaTrabajo.fecha >= fecha_desde,
            RutaTrabajo.fecha <= fecha_hasta,
            RutaItem.fotos_pendientes_cerradas_at.is_(None),
        )
    )
    aggregate = apply_completar_trabajo_inspector_scope(aggregate, inspector_id_effective)

    rows = (
        aggregate.group_by(RutaTrabajo.fecha)
        .having(func.count(RutaItem.id) > 0)
        .order_by(RutaTrabajo.fecha.asc())
        .all()
    )

    dias = [
        dia_resumen_completar_trabajo_pendientes(
            fecha_dia=row.fecha,
            total=int(row.pendientes_cierre or 0),
            items_con_actuacion=int(row.items_con_actuacion or 0),
            hoy=hoy,
        )
        for row in rows
    ]

    meta = {
        "fecha_desde": fecha_desde.isoformat(),
        "fecha_hasta": fecha_hasta.isoformat(),
        "hoy": hoy.isoformat(),
    }
    return dias, meta
