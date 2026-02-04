from __future__ import annotations

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
    return DomicilioGeocode.query.get(domicilio_id)


def get_or_create_geocode(domicilio_id: int) -> DomicilioGeocode:
    """
    Obtiene o crea (sin commit) el registro de geocodificación.

    Args:
        domicilio_id: id del domicilio.

    Returns:
        Instancia de DomicilioGeocode existente o nueva.
    """
    existing = DomicilioGeocode.query.get(domicilio_id)
    if existing:
        return existing
    geo = DomicilioGeocode(domicilio_id=domicilio_id)
    db.session.add(geo)
    db.session.flush()
    return geo
