from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import func, exists, or_, and_

from app.database import db
from app.models import Actuaciones, Domicilio, Expediente, Notificacion
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    list_reinspeccion_notificacion_operativas,
    materializacion_notificacion_vencida_on_read_enabled,
    sync_iniciadores_reinspeccion_notificacion,
)


def _apply_fecha(query, desde, hasta):
    if desde:
        query = query.filter(Actuaciones.fecha >= desde)
    if hasta:
        query = query.filter(Actuaciones.fecha <= hasta)
    return query


def _apply_distrito_optional(query, distrito_id: Optional[int]):
    """Restringe por ``domicilio.distrito_id`` (join único)."""
    if distrito_id is None:
        return query
    return query.join(Domicilio, Actuaciones.domicilio_id == Domicilio.id).filter(
        Domicilio.distrito_id == int(distrito_id)
    )


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
    Bandeja de gestión de expedientes de plazo por rama NOTIFICACION.

    Regla para este slice:
    - actuación con notificación
    - sin comprobación (si hay ambas domina COMPROBACION)

    Nota: puede haber 0..N expedientes `PRORROGA_NOTIFICACION` por notificación; la fila sigue
    apareciendo (gestión continua). Métricas `dias_restantes` / `plazos_otorgados` en presenter.
    """
    query = (
        Actuaciones.query.filter(Actuaciones.notificacion_id.isnot(None))
        .filter(Actuaciones.comprobacion_id.is_(None))
    )
    return _apply_fecha(query, filters.desde, filters.hasta)


def build_notificacion_expediente_bandeja_metrics(
    acts: List[Actuaciones],
) -> tuple[dict[int, int], dict[int, date | None]]:
    """
    Para actuaciones NOTIFICACION-only: cuenta expedientes de plazo por `notificacion_id` y
    carga `fecha_vencimiento` desde `Notificacion` (batch, evita N+1 en la bandeja).
    """
    noti_ids = list(
        {
            int(a.notificacion_id)
            for a in acts
            if a.notificacion_id is not None and a.comprobacion_id is None
        }
    )
    if not noti_ids:
        return {}, {}

    rows = (
        db.session.query(Expediente.notificacion_id, func.count(Expediente.id))
        .filter(Expediente.notificacion_id.in_(noti_ids))
        .filter(Expediente.tipo_expediente == "PRORROGA_NOTIFICACION")
        .filter(Expediente.deleted_at.is_(None))
        .group_by(Expediente.notificacion_id)
        .all()
    )
    plazos_map: dict[int, int] = {int(nid): int(c) for nid, c in rows}

    notis = Notificacion.query.filter(Notificacion.id.in_(noti_ids)).all()
    venc_map: dict[int, date | None] = {int(n.id): n.fecha_vencimiento for n in notis}

    return plazos_map, venc_map


def _notificaciones_pendientes_query(filters: ActuacionesPendientesFilters):
    """
    Retorna query operativa para notificaciones vencidas con iniciador materializado.

    Fase C: la materialización corre por CLI / `flask sync-notificaciones-vencidas` / scheduler, no por este
    GET. Solo si `SYNC_NOTIFICACIONES_VENCIDAS_ON_READ=1` se invoca sync aquí (compatibilidad transitoria).

    Luego filtramos por rango de fecha de actuación para mantener contrato del endpoint.
    """
    if materializacion_notificacion_vencida_on_read_enabled():
        sync_iniciadores_reinspeccion_notificacion()
    act_ids = [a.id for a in list_reinspeccion_notificacion_operativas()]
    if not act_ids:
        return Actuaciones.query.filter(False)
    query = Actuaciones.query.filter(Actuaciones.id.in_(act_ids))
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
    distrito_id = getattr(filters, "distrito_id", None)

    if source_type == "comprobacion":
        query = _apply_distrito_optional(_sin_expediente_query(filters), distrito_id)
    elif source_type == "notificacion":
        query = _apply_distrito_optional(_sin_expediente_notificacion_query(filters), distrito_id)
    else:
        query_comp = _apply_distrito_optional(_sin_expediente_query(filters), distrito_id)
        query_noti = _apply_distrito_optional(_sin_expediente_notificacion_query(filters), distrito_id)
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
    query = _apply_distrito_optional(query, getattr(filters, "distrito_id", None))
    return query.order_by(Actuaciones.id.desc()).all()
