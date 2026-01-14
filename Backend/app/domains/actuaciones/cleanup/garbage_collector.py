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
    if any_act is not None:
        return

    domicilio.deleted_at = datetime.utcnow()
    db.session.add(domicilio)


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

