from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List

from sqlalchemy import func, exists, or_, select, and_, inspect as sa_inspect

from app.database import db
from app.models import Actuaciones, Domicilio, Expediente
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters


def _apply_fecha(query, desde, hasta):
    if desde:
        query = query.filter(Actuaciones.fecha >= desde)
    if hasta:
        query = query.filter(Actuaciones.fecha <= hasta)
    return query


@lru_cache(maxsize=1)
def _has_expediente_notificacion_id_column() -> bool:
    """
    Detecta si la columna `expediente.notificacion_id` existe en la DB conectada.

    Evita 500 cuando el código fue desplegado pero la migración aún no corrió.
    """
    inspector = sa_inspect(db.engine)
    cols = inspector.get_columns("expediente")
    col_names = {c.get("name") for c in cols}
    return "notificacion_id" in col_names


def _domicilios_pendientes_query(filters: ActuacionesPendientesFilters):
    query = (
        Actuaciones.query.join(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .filter(Domicilio.deleted_at.is_(None))
        .filter(
            or_(
                Domicilio.calle_norm_status.is_(None),
                Domicilio.calle_norm_status != "OK",
                and_(
                    Domicilio.numero_tipo == "ESQUINA",
                    or_(
                        Domicilio.esquina_norm_status.is_(None),
                        Domicilio.esquina_norm_status != "OK",
                    ),
                ),
            )
        )
    )
    return _apply_fecha(query, filters.desde, filters.hasta)


def _sin_expediente_query(filters: ActuacionesPendientesFilters):
    subq = exists().where(Expediente.comprobacion_id == Actuaciones.comprobacion_id)
    query = (
        Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(~subq)
    )
    return _apply_fecha(query, filters.desde, filters.hasta)


def _sin_expediente_notificacion_query(filters: ActuacionesPendientesFilters):
    """
    Pendientes de expediente por rama NOTIFICACION.

    Regla para este slice:
    - actuación con notificación
    - sin comprobación (si hay ambas domina COMPROBACION)
    - sin expediente asociado por su notificación
    """
    query = (
        Actuaciones.query.filter(Actuaciones.notificacion_id.isnot(None))
        .filter(Actuaciones.comprobacion_id.is_(None))
    )
    if _has_expediente_notificacion_id_column():
        subq = exists().where(Expediente.notificacion_id == Actuaciones.notificacion_id)
        query = query.filter(~subq)
    return _apply_fecha(query, filters.desde, filters.hasta)


def _notificaciones_pendientes_query(filters: ActuacionesPendientesFilters):
    base = (
        Actuaciones.query
        .filter(Actuaciones.notificacion_id.isnot(None))
    )
    base = _apply_fecha(base, filters.desde, filters.hasta)

    subq = (
        base.with_entities(Actuaciones.notificacion_id)
        .group_by(Actuaciones.notificacion_id)
        .having(func.count(Actuaciones.id) == 1)
        .subquery()
    )

    query = Actuaciones.query.filter(
        Actuaciones.notificacion_id.in_(select(subq.c.notificacion_id))
    )
    return _apply_fecha(query, filters.desde, filters.hasta)


def get_pendientes_summary(filters: ActuacionesPendientesFilters) -> Dict[str, int]:
    """
    Obtiene conteos de pendientes de Actuaciones (domicilios, sin expediente, notificaciones).
    """
    domicilios = _domicilios_pendientes_query(filters).count()
    sin_expediente = _sin_expediente_query(filters).count()
    notificaciones = _notificaciones_pendientes_query(filters).count()
    total = domicilios + sin_expediente + notificaciones

    return {
        "total": total,
        "domicilios": domicilios,
        "sin_expediente": sin_expediente,
        "notificaciones": notificaciones,
    }


def get_pendientes_list(filters: ActuacionesPendientesFilters) -> List[Actuaciones]:
    """
    Lista actuaciones pendientes según tipo:
      - domicilios
      - sin_expediente
      - notificaciones
    """
    if filters.tipo == "domicilios":
        query = _domicilios_pendientes_query(filters)
    elif filters.tipo == "sin_expediente":
        query = _sin_expediente_query(filters)
    elif filters.tipo == "notificaciones":
        query = _notificaciones_pendientes_query(filters)
    else:
        return []

    return query.order_by(Actuaciones.id.desc()).all()


def get_pendientes_expediente(filters: ActuacionesPendientesFilters) -> List[Actuaciones]:
    """
    Lista actuaciones pendientes de expediente.

    Reutiliza y unifica la lógica administrativa para dos ramas:
    - COMPROBACION: actuación con comprobación sin expediente en su comprobación.
    - NOTIFICACION: actuación con notificación sin comprobación (dominancia de comprobación).

    source_type (filtro):
    - all
    - notificacion
    - comprobacion
    """
    source_type = (filters.source_type or "all").lower()

    if source_type == "comprobacion":
        query = _sin_expediente_query(filters)
    elif source_type == "notificacion":
        query = _sin_expediente_notificacion_query(filters)
    else:
        query_comp = _sin_expediente_query(filters)
        query_noti = _sin_expediente_notificacion_query(filters)
        query = query_comp.union(query_noti)

    return query.order_by(Actuaciones.id.desc()).all()


def get_pendientes_oficio(filters: ActuacionesPendientesFilters) -> List[Actuaciones]:
    """
    Lista actuaciones en estado "esperando oficio".

    Reglas:
    - Debe pertenecer a rama COMPROBACION (`comprobacion_id` no nulo).
    - Debe existir expediente original de comprobación (ENVIO_ACTA u otro sin oficio).
    - No debe existir expediente de respuesta de oficio para esa comprobación.
    """
    has_expediente_original = exists().where(
        (Expediente.comprobacion_id == Actuaciones.comprobacion_id)
        & (Expediente.oficio_id.is_(None))
    )
    has_respuesta_oficio = exists().where(
        (Expediente.comprobacion_id == Actuaciones.comprobacion_id)
        & (Expediente.oficio_id.isnot(None))
        & (func.upper(Expediente.tipo_expediente) == "RESPUESTA_OFICIO")
    )

    query = (
        Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(has_expediente_original)
        .filter(~has_respuesta_oficio)
    )
    query = _apply_fecha(query, filters.desde, filters.hasta)
    return query.order_by(Actuaciones.id.desc()).all()
