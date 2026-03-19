from __future__ import annotations

from datetime import date

from flask_jwt_extended import get_jwt_identity
from sqlalchemy import and_, exists
from sqlalchemy.orm import aliased

from app.database import db
from app.models import Actuaciones, Domicilio, IniciadorRuta, Notificacion, User
from app.domains.rutas_trabajo.services.iniciador_policy_service import (
    inactive_estados,
    priority_for_tipo,
)


def _get_current_user_id() -> int:
    """
    Resuelve user_id autenticado para auditoría.

    Compatibilidad:
    - Si no hay contexto JWT (ruta legacy), usa un usuario activo como fallback.
    """
    try:
        identity = get_jwt_identity()
    except Exception:
        identity = None

    user_id = identity.get("user_id") if isinstance(identity, dict) else identity
    if user_id is not None:
        try:
            parsed_id = int(user_id)
        except (TypeError, ValueError):
            parsed_id = None
        if parsed_id is not None:
            user = User.query.get(parsed_id)
            if user and getattr(user, "is_active", True):
                return parsed_id

    fallback_user = User.query.filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
    if fallback_user:
        return int(fallback_user.id)
    raise ValueError("No hay usuario activo para registrar created_by_user_id")


def _eligible_inspecciones_vencidas() -> list[Actuaciones]:
    """
    Retorna actuaciones base INSPECCION elegibles para crear iniciador por
    vencimiento de notificación.

    Elegibilidad:
    - notificación no borrada.
    - fecha_vencimiento no nula y <= hoy.
    - actuación base de tipo INSPECCION.
    - domicilio operativo (domicilio_id no nulo y domicilio no soft-deleteado).
    - sin reinspección ya registrada para la misma notificación.
    """
    today = date.today()
    A2 = aliased(Actuaciones)
    subq_reinsp = exists().where(
        and_(
            A2.notificacion_id == Actuaciones.notificacion_id,
            A2.tipo == "REINSPECCION",
        )
    )
    return (
        Actuaciones.query
        .join(Notificacion, Notificacion.id == Actuaciones.notificacion_id)
        .join(Domicilio, Domicilio.id == Actuaciones.domicilio_id)
        .filter(Actuaciones.tipo == "INSPECCION")
        .filter(Actuaciones.notificacion_id.isnot(None))
        .filter(Actuaciones.domicilio_id.isnot(None))
        .filter(Domicilio.deleted_at.is_(None))
        .filter(Notificacion.deleted_at.is_(None))
        .filter(Notificacion.fecha_vencimiento.isnot(None))
        .filter(Notificacion.fecha_vencimiento <= today)
        .filter(~subq_reinsp)
        .order_by(Actuaciones.id.desc())
        .all()
    )


def _has_active_iniciador_notificacion(notificacion_id: int) -> bool:
    iniciador = (
        IniciadorRuta.query.filter(
            IniciadorRuta.notificacion_id == notificacion_id,
            IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador.notin_(inactive_estados()),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )
    return iniciador is not None


def sync_iniciadores_reinspeccion_notificacion() -> int:
    """
    Materializa iniciadores derivados para notificaciones vencidas.

    Crea solo cuando corresponde y con idempotencia:
    - si ya existe iniciador activo para la notificación, no duplica;
    - si en la misma corrida aparecen múltiples actuaciones base para una
      misma notificación, materializa una sola vez.
    """
    created = 0
    processed_notificacion_ids: set[int] = set()
    user_id = _get_current_user_id()
    today = date.today()

    for act in _eligible_inspecciones_vencidas():
        noti = act.notificacion
        if not noti or not noti.fecha_vencimiento:
            continue
        if noti.deleted_at is not None:
            continue
        if noti.fecha_vencimiento > today:
            continue
        if not act.domicilio_id:
            continue
        notificacion_id = int(noti.id)
        if notificacion_id in processed_notificacion_ids:
            continue
        if _has_active_iniciador_notificacion(notificacion_id):
            processed_notificacion_ids.add(notificacion_id)
            continue

        iniciador = IniciadorRuta(
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="PENDIENTE",
            fecha_origen=noti.fecha_vencimiento,
            anio=int(noti.fecha_vencimiento.year),
            mes=int(noti.fecha_vencimiento.month),
            domicilio_id=int(act.domicilio_id),
            prioridad=priority_for_tipo("REINSPECCION_NOTIFICACION"),
            notificacion_id=notificacion_id,
            actuacion_id=act.id,
            created_by_user_id=user_id,
            observaciones=(
                f"Derivado automático por vencimiento de notificación "
                f"{noti.numero_acta}/{noti.anio}"
            ),
        )
        db.session.add(iniciador)
        processed_notificacion_ids.add(notificacion_id)
        created += 1

    if created > 0:
        db.session.commit()
    return created


def list_reinspeccion_notificacion_operativas() -> list[Actuaciones]:
    """
    Lista actuaciones base con iniciador derivado de notificación en estado pendiente.
    """
    A2 = aliased(Actuaciones)
    subq_reinsp = exists().where(
        and_(
            A2.notificacion_id == Actuaciones.notificacion_id,
            A2.tipo == "REINSPECCION",
        )
    )
    return (
        Actuaciones.query
        .join(IniciadorRuta, IniciadorRuta.actuacion_id == Actuaciones.id)
        .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION")
        .filter(IniciadorRuta.estado_iniciador == "PENDIENTE")
        .filter(IniciadorRuta.deleted_at.is_(None))
        .filter(~subq_reinsp)
        .order_by(Actuaciones.id.desc())
        .all()
    )

