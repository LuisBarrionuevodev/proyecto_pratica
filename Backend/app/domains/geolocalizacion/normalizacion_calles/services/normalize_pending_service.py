from __future__ import annotations

from typing import Dict

from app.database import db
from app.domains.geolocalizacion.normalizacion_calles.repos.domicilio_repo import list_pendientes
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    _normalize_calle,
    _normalize_esquina,
)


def normalizar_pendientes(limit: int = 200, only: str | None = None) -> Dict[str, object]:
    """
    Normaliza domicilios pendientes en batch.
    """
    if only not in (None, "calle", "esquina", "both"):
        raise ValueError("El parámetro 'only' debe ser calle, esquina o both.")
    effective_only = None if only in (None, "both") else only
    items = list_pendientes(limit, only=effective_only)
    ok_count = 0
    no_match_count = 0
    ambigua_count = 0
    esquina_ok_count = 0
    esquina_no_match_count = 0
    esquina_ambigua_count = 0
    processed = 0

    for idx, dom in enumerate(items, start=1):
        if effective_only in (None, "calle"):
            calle_result = _normalize_calle(dom)
            if calle_result:
                if calle_result["status"] == "OK":
                    ok_count += 1
                elif calle_result["status"] == "REVIEW":
                    ambigua_count += 1
                else:
                    no_match_count += 1

        if effective_only in (None, "esquina"):
            esquina_result = _normalize_esquina(dom)
            if esquina_result:
                if esquina_result["status"] == "OK":
                    esquina_ok_count += 1
                elif esquina_result["status"] == "REVIEW":
                    esquina_ambigua_count += 1
                else:
                    esquina_no_match_count += 1

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
        "esquina_ok_count": esquina_ok_count,
        "esquina_no_match_count": esquina_no_match_count,
        "esquina_ambigua_count": esquina_ambigua_count,
    }
