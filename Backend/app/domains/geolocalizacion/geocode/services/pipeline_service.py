from __future__ import annotations

from typing import Dict

from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio,
)
from app.domains.geolocalizacion.geocoding.services.geocode_service import (
    geocode_domicilio,
)


def pipeline_post_commit(domicilio_id: int) -> Dict[str, object]:
    """
    Pipeline post-commit: normaliza y geocodifica si corresponde.

    - Normaliza calle/esquina
    - Si queda OK -> geocodifica
    - Tolerante a errores (no debe romper el flujo principal)
    """
    result: Dict[str, object] = {"domicilio_id": domicilio_id}
    try:
        norm = normalizar_domicilio(domicilio_id)
        result["normalizacion"] = norm
    except Exception as exc:  # noqa: BLE001
        result["normalizacion_error"] = str(exc)
        return result

    try:
        geo = geocode_domicilio(domicilio_id)
        result["geocode"] = geo
    except Exception as exc:  # noqa: BLE001
        result["geocode_error"] = str(exc)
    return result
