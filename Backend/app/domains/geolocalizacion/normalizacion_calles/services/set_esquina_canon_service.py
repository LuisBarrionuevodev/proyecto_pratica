from __future__ import annotations

from datetime import datetime
from typing import Dict

from app.database import db
from app.models import CalleCatalogo
from app.domains.geolocalizacion.normalizacion_calles.repos.domicilio_repo import get_domicilio


def set_esquina_canon(domicilio_id: int, esquina_catalogo_id: int) -> Dict[str, object]:
    """
    Setea una esquina canónica en un domicilio y marca normalización OK.
    """
    dom = get_domicilio(domicilio_id)
    if not dom:
        raise ValueError("Domicilio no encontrado.")

    calle = CalleCatalogo.query.get(esquina_catalogo_id)
    if not calle:
        raise ValueError("Calle de catálogo no encontrada.")

    dom.esquina_catalogo_id = calle.id
    dom.esquina_normalizada = calle.nombre_canonico
    dom.esquina_norm_status = "OK"
    dom.esquina_norm_score = 1
    dom.esquina_norm_error = None
    dom.esquina_norm_updated_at = datetime.utcnow()

    db.session.add(dom)
    db.session.commit()

    return {
        "ok": True,
        "domicilio_id": dom.id,
        "esquina_catalogo_id": dom.esquina_catalogo_id,
        "esquina_normalizada": dom.esquina_normalizada,
        "esquina_estado": dom.esquina_norm_status,
        "esquina_score": dom.esquina_norm_score,
    }
