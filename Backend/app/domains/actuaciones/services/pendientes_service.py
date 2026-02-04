from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import func, exists, or_, select, and_

from app.models import Actuaciones, Domicilio, Expediente
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters


def _apply_fecha(query, desde, hasta):
    if desde:
        query = query.filter(Actuaciones.fecha >= desde)
    if hasta:
        query = query.filter(Actuaciones.fecha <= hasta)
    return query


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
