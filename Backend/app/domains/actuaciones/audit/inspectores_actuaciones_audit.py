"""
Inventario de inspectores por actuación (tabla `actuaciones_inspector`).

Sirve para medir cuántas actuaciones tienen más de N inspectores activos antes de
cambiar el contrato de grilla (inspector1/2/3) por listas arbitrarias.

Solo enlaces con ``deleted_at IS NULL`` cuentan como activos (alineado a mapas/indicadores).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func

from app.database import db
from app.models.actuaciones_inspector import actuaciones_inspector

logger = logging.getLogger(__name__)


def count_active_inspectores_for_actuacion(actuacion_id: int) -> int:
    """
    Cantidad de inspectores activos vinculados a la actuación (filas no borradas en la tabla puente).

    Parámetros:
        actuacion_id: PK de ``actuaciones``.

    Retorno:
        Entero >= 0.
    """
    n = (
        db.session.query(func.count())
        .select_from(actuaciones_inspector)
        .filter(
            actuaciones_inspector.c.actuaciones_id == actuacion_id,
            actuaciones_inspector.c.deleted_at.is_(None),
        )
        .scalar()
    )
    return int(n or 0)


def _distribution_rows() -> list[tuple[int, int]]:
    """
    Por cada actuación con al menos un inspector activo, devuelve (actuaciones_id, cantidad).

    Orden: cantidad descendente, luego id de actuación.
    """
    q = (
        db.session.query(
            actuaciones_inspector.c.actuaciones_id.label("aid"),
            func.count().label("n"),
        )
        .filter(actuaciones_inspector.c.deleted_at.is_(None))
        .group_by(actuaciones_inspector.c.actuaciones_id)
        .order_by(func.count().desc(), actuaciones_inspector.c.actuaciones_id.asc())
    )
    return [(int(r.aid), int(r.n)) for r in q.all()]


def audit_actuaciones_inspectores_summary(*, max_detail_ids: int = 200) -> dict[str, Any]:
    """
    Resumen para CLI / informes: distribución y detección de actuaciones con más de 3 inspectores.

    Parámetros:
        max_detail_ids: máximo de ids listados en ``actuacion_ids_mas_de_3``.

    Retorno:
        Dict serializable con totales y listas de ids.
    """
    rows = _distribution_rows()
    counts = [n for _, n in rows]
    if not counts:
        return {
            "actuaciones_con_al_menos_un_inspector": 0,
            "max_inspectores_por_actuacion": 0,
            "con_mas_de_3_inspectores": 0,
            "actuacion_ids_mas_de_3": [],
            "detalle_mas_de_3": [],
            "buckets_por_cantidad": {"1": 0, "2": 0, "3": 0, "4+": 0},
        }

    buckets = {"1": 0, "2": 0, "3": 0, "4+": 0}
    for n in counts:
        if n >= 4:
            buckets["4+"] += 1
        else:
            buckets[str(n)] += 1

    mas_de_3 = sorted(
        [(aid, n) for aid, n in rows if n > 3],
        key=lambda t: (-t[1], t[0]),
    )

    return {
        "actuaciones_con_al_menos_un_inspector": len(rows),
        "max_inspectores_por_actuacion": max(counts),
        "con_mas_de_3_inspectores": len(mas_de_3),
        "actuacion_ids_mas_de_3": [aid for aid, _ in mas_de_3[:max_detail_ids]],
        "detalle_mas_de_3": [{"actuacion_id": aid, "inspectores_activos": n} for aid, n in mas_de_3[:max_detail_ids]],
        "buckets_por_cantidad": buckets,
    }


def log_truncation_risk_if_applicable(
    *,
    actuacion_id: int,
    payload_inspectores_nombres: list[str],
) -> None:
    """
    Registra en log (WARNING) un posible riesgo de truncado al guardar desde la grilla.

    Escenario: la actuación ya tiene más de 3 inspectores en DB y el payload solo puede
    traer hasta 3 nombres (canal CargarActuacion / ``map_actuacion_row``). Cualquier
    reducción a <=3 nombres podría ser edición intencional **o** un guardado que pierde el 4º+.

    No bloquea el guardado: solo deja trazabilidad para operación y el siguiente PR estructural.

    Parámetros:
        actuacion_id: actuación que se está actualizando.
        payload_inspectores_nombres: lista ya normalizada (sin vacíos) que irá a ``get_inspectores_o_falla``.
    """
    n_cur = count_active_inspectores_for_actuacion(actuacion_id)
    n_in = len(payload_inspectores_nombres)
    if n_cur <= 3:
        return
    if n_in > 3:
        return
    logger.warning(
        "inspectores_truncation_risk: actuación id=%s tenía %s inspectores activos; "
        "el payload envía %s (≤3). Puede ser reducción válida o pérdida por límite de grilla — "
        "revisar antes del próximo cambio de contrato.",
        actuacion_id,
        n_cur,
        n_in,
    )
