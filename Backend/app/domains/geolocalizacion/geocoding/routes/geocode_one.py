from __future__ import annotations

from flask import jsonify

from app.domains.geolocalizacion.geocoding.services.geocode_service import (
    geocode_domicilio,
)
from . import geolocalizacion_geocode


@geolocalizacion_geocode.post("/geolocalizacion/geocode/<int:domicilio_id>")
def geocode_one(domicilio_id: int):
    """
    Geocodifica un domicilio específico.
    """
    try:
        result = geocode_domicilio(domicilio_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e), "domicilio_id": domicilio_id}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "domicilio_id": domicilio_id}), 500
