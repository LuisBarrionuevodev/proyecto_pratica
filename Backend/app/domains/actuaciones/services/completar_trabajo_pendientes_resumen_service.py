from __future__ import annotations

from datetime import date

from sqlalchemy import case, func

from app.database import db
from app.models import RutaItem, RutaTrabajo

from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    dia_resumen_completar_trabajo_pendientes,
)


def list_completar_trabajo_pendientes_resumen_por_dia(
    *,
    fecha_desde: date,
    fecha_hasta: date,
) -> tuple[list[dict], dict]:
    """
    Agrega por día operativo de ruta publicada el ámbito Completar trabajo.

    **Actividad del día** (consistente con el listado por fecha): existe al menos un
    `RutaItem` no borrado, con `actuacion_id`, en una `RutaTrabajo` PUBLICADA con esa
    `fecha`. Es la misma base de datos que alimenta el grid (actuación mínima generada
    al publicar).

    Por cada día con actividad se devuelve:
    - `total`: cantidad EN_PROCESO (pendientes de cierre; mismo criterio que GET pendientes).
    - `items_con_actuacion`: total de ítems en ese ámbito (cualquier `estado_ruta_item`).
    - `categoria_calendario`: CON_PENDIENTES si `total`>0, si no COMPLETO (actividad sin cierres pendientes).

    Fechas sin fila: sin actividad en este módulo para el rango consultado.

    Parámetros:
        fecha_desde: inicio inclusive (`RutaTrabajo.fecha`).
        fecha_hasta: fin inclusive.

    Retorno:
        Tupla (`dias`, `meta`). `dias` incluye **todos** los días con actividad (incluso `total==0`),
        orden cronológico.

    Errores:
        Ninguno desde servicio; validación de rango en capa Pydantic de la ruta.
    """
    hoy = date.today()

    pendientes_expr = func.sum(
        case((RutaItem.estado_ruta_item == "EN_PROCESO", 1), else_=0)
    ).label("pendientes_cierre")
    items_expr = func.count(RutaItem.id).label("items_con_actuacion")

    rows = (
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
        )
        .group_by(RutaTrabajo.fecha)
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
