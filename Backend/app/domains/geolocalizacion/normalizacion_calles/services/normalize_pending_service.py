from __future__ import annotations

from datetime import datetime
from typing import Dict

from app.database import db
from app.domains.geolocalizacion.normalizacion_calles.repos.domicilio_repo import list_pendientes
from app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service import match_calle
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key


def normalizar_pendientes(limit: int = 200) -> Dict[str, object]:
    """
    Normaliza domicilios pendientes en batch.
    """
    items = list_pendientes(limit)
    ok_count = 0
    no_match_count = 0
    ambigua_count = 0
    processed = 0

    for idx, dom in enumerate(items, start=1):
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
            ok_count += 1
        elif result["status"] == "REVIEW":
            dom.calle_normalizada = None
            dom.calle_catalogo_id = None
            dom.calle_norm_status = "REVIEW"
            dom.calle_norm_score = result["score"]
            dom.calle_norm_error = "review"
            ambigua_count += 1
        else:
            dom.calle_normalizada = None
            dom.calle_catalogo_id = None
            dom.calle_norm_status = "NO_MATCH"
            dom.calle_norm_score = result["score"]
            dom.calle_norm_error = "no match"
            no_match_count += 1

        db.session.add(dom)
        processed += 1
        if idx % 50 == 0:
            db.session.commit()

    db.session.commit()

    return {
        "ok": True,
        "processed": processed,
        "ok_count": ok_count,
        "no_match_count": no_match_count,
        "ambigua_count": ambigua_count,
    }
