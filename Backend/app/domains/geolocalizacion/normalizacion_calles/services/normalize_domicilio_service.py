from __future__ import annotations

from datetime import datetime
from typing import Dict

from app.database import db
from app.domains.geolocalizacion.normalizacion_calles.repos.domicilio_repo import get_domicilio
from app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service import match_calle
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key


def normalizar_domicilio(domicilio_id: int) -> Dict[str, object]:
    """
    Normaliza la calle de un domicilio y persiste resultado.
    """
    dom = get_domicilio(domicilio_id)
    if not dom:
        raise ValueError("Domicilio no encontrado.")
    if not dom.calle:
        raise ValueError("Domicilio sin calle.")

    if dom.calle_raw is None:
        dom.calle_raw = dom.calle

    key = slug_key(dom.calle)
    result = match_calle(dom.calle)

    dom.calle_key = key
    dom.calle_norm_updated_at = datetime.utcnow()

    if result["status"] == "OK":
        dom.calle_normalizada = result["canon"]
        dom.calle_catalogo_id = result["catalogo_id"]
        dom.calle_norm_status = "OK"
        dom.calle_norm_score = result["score"]
        dom.calle_norm_error = None
    elif result["status"] == "REVIEW":
        dom.calle_normalizada = None
        dom.calle_catalogo_id = None
        dom.calle_norm_status = "REVIEW"
        dom.calle_norm_score = result["score"]
        dom.calle_norm_error = "review"
    else:
        dom.calle_normalizada = None
        dom.calle_catalogo_id = None
        dom.calle_norm_status = "NO_MATCH"
        dom.calle_norm_score = result["score"]
        dom.calle_norm_error = "no match"

    db.session.add(dom)
    db.session.commit()

    return {
        "ok": True,
        "status": dom.calle_norm_status,
        "canon": dom.calle_normalizada,
        "score": dom.calle_norm_score,
        "error": dom.calle_norm_error,
        "suggestions": result.get("candidates"),
        "domicilio_id": dom.id,
    }
