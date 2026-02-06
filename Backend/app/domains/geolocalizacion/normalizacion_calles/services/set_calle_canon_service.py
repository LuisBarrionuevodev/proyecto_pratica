from __future__ import annotations

from datetime import datetime
from typing import Dict

from app.database import db
from app.models import CalleCatalogo
from app.domains.geolocalizacion.normalizacion_calles.repos.domicilio_repo import get_domicilio
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    on_domicilio_changed,
)


def set_calle_canon(domicilio_id: int, calle_catalogo_id: int) -> Dict[str, object]:
    """
    Setea una calle canónica en un domicilio y marca normalización OK.
    """
    dom = get_domicilio(domicilio_id)
    if not dom:
        raise ValueError("Domicilio no encontrado.")

    calle = CalleCatalogo.query.get(calle_catalogo_id)
    if not calle:
        raise ValueError("Calle de catálogo no encontrada.")

    dom.calle_catalogo_id = calle.id
    dom.calle_normalizada = calle.nombre_canonico
    dom.calle_norm_status = "OK"
    dom.calle_norm_score = 1
    dom.calle_norm_error = None
    dom.calle_norm_updated_at = datetime.utcnow()

    db.session.add(dom)
    db.session.commit()

    try:
        on_domicilio_changed(dom.id)
    except Exception:
        pass

    return {
        "ok": True,
        "domicilio_id": dom.id,
        "calle_catalogo_id": dom.calle_catalogo_id,
        "calle_normalizada": dom.calle_normalizada,
        "calle_estado": dom.calle_norm_status,
        "calle_score": dom.calle_norm_score,
    }
