from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.database import db
from app.models import DomicilioGeocode


def get_geocode(domicilio_id: int) -> Optional[DomicilioGeocode]:
    """
    Obtiene el registro de geocodificación por domicilio.

    Args:
        domicilio_id: id del domicilio.

    Returns:
        DomicilioGeocode o None si no existe.
    """
    return (
        DomicilioGeocode.query.filter(
            DomicilioGeocode.domicilio_id == domicilio_id,
            DomicilioGeocode.deleted_at.is_(None),
        )
        .limit(1)
        .first()
    )


def get_or_create_geocode(domicilio_id: int) -> DomicilioGeocode:
    """
    Obtiene o crea (sin commit) el registro de geocodificación.

    Args:
        domicilio_id: id del domicilio.

    Returns:
        Instancia de DomicilioGeocode existente o nueva.
    """
    existing = get_geocode(domicilio_id)
    if existing:
        return existing
    deleted = (
        DomicilioGeocode.query.filter(DomicilioGeocode.domicilio_id == domicilio_id)
        .limit(1)
        .first()
    )
    if deleted:
        deleted.deleted_at = None
        deleted.checked_at = None
        deleted.error_msg = None
        db.session.add(deleted)
        return deleted
    geo = DomicilioGeocode(domicilio_id=domicilio_id)
    db.session.add(geo)
    db.session.flush()
    return geo


def ensure_geocode_row(domicilio_id: int) -> DomicilioGeocode:
    """
    Garantiza la existencia de un row de geocode para un domicilio.

    Args:
        domicilio_id: id del domicilio.

    Returns:
        DomicilioGeocode existente o nuevo.
    """
    return get_or_create_geocode(domicilio_id)


def soft_delete_geocode_if_exists(domicilio_id: int) -> None:
    """
    Soft delete lógico del geocode asociado a un domicilio.

    Args:
        domicilio_id: id del domicilio.
    """
    geo = (
        DomicilioGeocode.query.filter(
            DomicilioGeocode.domicilio_id == domicilio_id,
            DomicilioGeocode.deleted_at.is_(None),
        )
        .limit(1)
        .first()
    )
    if not geo:
        return
    geo.deleted_at = datetime.utcnow()
    db.session.add(geo)
