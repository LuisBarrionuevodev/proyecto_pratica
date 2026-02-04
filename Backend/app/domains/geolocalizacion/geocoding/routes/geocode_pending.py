from __future__ import annotations

from flask import jsonify, request

from app.domains.geolocalizacion.geocoding.services.geocode_pending_service import (
    geocode_pendientes,
)
from . import geolocalizacion_geocode


@geolocalizacion_geocode.post("/geolocalizacion/geocode-pending")
def geocode_pending():
    """
    Geocodifica domicilios pendientes en batch.
    """
    try:
        limit = int(request.args.get("limit", 200))
        summary = geocode_pendientes(limit=limit)
        return jsonify({"ok": True, **summary}), 200
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
