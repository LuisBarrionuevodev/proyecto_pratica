"""Garbage collector (limpieza post-update) para soft delete.

Este módulo contiene funciones idempotentes que marcan como "borrado lógico"
(`deleted_at`) entidades que quedan huérfanas luego de updates.

Regla clave: **no hace commit**. Solo modifica el objeto y hace `db.session.add(...)`.
"""

from __future__ import annotations

from datetime import datetime

from app.database import db
from app.models.actuaciones import Actuaciones
from app.models.contribuyente import Contribuyente
from app.models.domicilio import Domicilio
from app.models.relevamiento import Relevamiento
from app.models.denuncia import Denuncia
from app.models.iniciador_ruta import IniciadorRuta
from app.models.orden_de_trabajo import OrdenTrabajo
from app.models.notificacion import Notificacion
from app.models.comprobacion import Comprobacion
from app.models.oficio import Oficio
from app.models.expediente import Expediente
from app.domains.geolocalizacion.geocoding.repos.domicilio_geocode_repo import (
    soft_delete_geocode_if_exists,
)


def soft_delete_domicilio_if_orphan(domicilio_id: int) -> None:
    """Soft delete de `Domicilio` si quedó huérfano de `Actuaciones`.

    Qué hace:
    - Si el domicilio no existe, no hace nada.
    - Si ya está soft-deleted (`deleted_at` no es NULL), no hace nada.
    - Si **ninguna** fila de `Actuaciones` lo referencia por `Actuaciones.domicilio_id`,
      setea `deleted_at = utcnow()` y hace `db.session.add(domicilio)`.

    Parámetros:
    - domicilio_id: id del domicilio a evaluar.

    Retorno:
    - None
    """
    domicilio: Domicilio | None = db.session.get(Domicilio, domicilio_id)
    if domicilio is None:
        return
    if domicilio.deleted_at is not None:
        return

    any_act = (
        db.session.query(Actuaciones.id)
        .filter(Actuaciones.domicilio_id == domicilio_id)
        .limit(1)
        .first()
    )
    any_rel = (
        db.session.query(Relevamiento.id)
        .filter(
            Relevamiento.domicilio_id == domicilio_id,
            Relevamiento.deleted_at.is_(None),
        )
        .limit(1)
        .first()
    )
    any_denuncia = (
        db.session.query(Denuncia.id)
        .filter(Denuncia.domicilio_id == domicilio_id, Denuncia.deleted_at.is_(None))
        .limit(1)
        .first()
    )
    any_iniciador = (
        db.session.query(IniciadorRuta.id)
        .filter(
            IniciadorRuta.domicilio_id == domicilio_id,
            IniciadorRuta.deleted_at.is_(None),
        )
        .limit(1)
        .first()
    )
    if (
        any_act is not None
        or any_rel is not None
        or any_denuncia is not None
        or any_iniciador is not None
    ):
        return

    domicilio.deleted_at = datetime.utcnow()
    db.session.add(domicilio)
    soft_delete_geocode_if_exists(domicilio_id)


def soft_delete_contribuyente_if_orphan(contribuyente_id: int) -> None:
    """Soft delete de `Contribuyente` si no tiene domicilios activos.

    Qué hace:
    - Si el contribuyente no existe, no hace nada.
    - Si ya está soft-deleted (`deleted_at` no es NULL), no hace nada.
    - Si **NO** existe ningún `Domicilio` con:
        - `Domicilio.contribuyente_id == contribuyente_id` y
        - `Domicilio.deleted_at IS NULL`
      entonces marca `Contribuyente.deleted_at = utcnow()` y hace `db.session.add(contribuyente)`.

    Parámetros:
    - contribuyente_id: id del contribuyente a evaluar.

    Retorno:
    - None
    """
    contribuyente: Contribuyente | None = db.session.get(Contribuyente, contribuyente_id)
    if contribuyente is None:
        return
    if contribuyente.deleted_at is not None:
        return

    any_active_dom = (
        db.session.query(Domicilio.id)
        .filter(
            Domicilio.contribuyente_id == contribuyente_id,
            Domicilio.deleted_at.is_(None),
        )
        .limit(1)
        .first()
    )
    if any_active_dom is not None:
        return

    contribuyente.deleted_at = datetime.utcnow()
    db.session.add(contribuyente)


def soft_delete_orden_id_orphan(orden_trabajo_id: int) -> None:
    """Soft delete de `OrdenTrabajo` si quedó huérfana de `Actuaciones`.

    Qué hace:
    - Si la OT no existe, no hace nada.
    - Si ya está soft-deleted (`deleted_at` no es NULL), no hace nada.
    - Si **ninguna** fila de `Actuaciones` la referencia, setea `deleted_at = utcnow()`.

    Parámetros:
    - orden_trabajo_id: id de la OT a evaluar.
    """
    ot: OrdenTrabajo | None = db.session.get(OrdenTrabajo, orden_trabajo_id)
    if ot is None:
        return
    if ot.deleted_at is not None:
        return

    any_act = (
        db.session.query(Actuaciones.id)
        .filter(Actuaciones.orden_trabajo_id == orden_trabajo_id)
        .limit(1)
        .first()
    )
    if any_act is not None:
        return

    ot.deleted_at = datetime.utcnow()
    db.session.add(ot)


def soft_delete_notificacion_if_orphan(notificacion_id: int) -> None:
    """Soft delete de `Notificacion` si quedó huérfana de `Actuaciones`."""
    noti: Notificacion | None = db.session.get(Notificacion, notificacion_id)
    if noti is None or noti.deleted_at is not None:
        return

    any_act = (
        db.session.query(Actuaciones.id)
        .filter(Actuaciones.notificacion_id == notificacion_id)
        .limit(1)
        .first()
    )
    if any_act is not None:
        return

    noti.deleted_at = datetime.utcnow()
    db.session.add(noti)


def soft_delete_comprobacion_if_orphan(comprobacion_id: int) -> None:
    """Soft delete de `Comprobacion` si quedó huérfana de `Actuaciones`."""
    comp: Comprobacion | None = db.session.get(Comprobacion, comprobacion_id)
    if comp is None or comp.deleted_at is not None:
        return

    any_act = (
        db.session.query(Actuaciones.id)
        .filter(Actuaciones.comprobacion_id == comprobacion_id)
        .limit(1)
        .first()
    )
    if any_act is not None:
        return

    comp.deleted_at = datetime.utcnow()
    db.session.add(comp)


def soft_delete_oficio_if_orphan(oficio_id: int) -> None:
    """Soft delete de `Oficio` si quedó huérfano de comprobación/expediente."""
    ofi: Oficio | None = db.session.get(Oficio, oficio_id)
    if ofi is None or ofi.deleted_at is not None:
        return

    comp_active = (
        db.session.query(Comprobacion.id)
        .filter(
            Comprobacion.id == ofi.comprobacion_id,
            Comprobacion.deleted_at.is_(None),
        )
        .first()
    )
    exp_active = (
        db.session.query(Expediente.id)
        .filter(
            Expediente.oficio_id == oficio_id,
            Expediente.deleted_at.is_(None),
        )
        .limit(1)
        .first()
    )
    if comp_active is not None or exp_active is not None:
        return

    ofi.deleted_at = datetime.utcnow()
    db.session.add(ofi)


def soft_delete_expediente_if_orphan(expediente_id: int) -> None:
    """Soft delete de `Expediente` si quedó huérfano de comprobación/oficio."""
    exp: Expediente | None = db.session.get(Expediente, expediente_id)
    if exp is None or exp.deleted_at is not None:
        return

    comp_active = (
        db.session.query(Comprobacion.id)
        .filter(
            Comprobacion.id == exp.comprobacion_id,
            Comprobacion.deleted_at.is_(None),
        )
        .first()
    )
    ofi_active = (
        db.session.query(Oficio.id)
        .filter(
            Oficio.id == exp.oficio_id,
            Oficio.deleted_at.is_(None),
        )
        .first()
    )
    if comp_active is not None or ofi_active is not None:
        return

    exp.deleted_at = datetime.utcnow()
    db.session.add(exp)

