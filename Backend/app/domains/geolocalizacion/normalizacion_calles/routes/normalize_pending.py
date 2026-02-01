from __future__ import annotations

from flask import jsonify, request

from app.domains.geolocalizacion.normalizacion_calles.services.normalize_pending_service import (
    normalizar_pendientes,
)

from . import geolocalizacion_calles


@geolocalizacion_calles.post("/geolocalizacion/calles/normalize-pending")
def normalize_pending():
    """
    Normaliza domicilios pendientes en batch.
    """
    try:
        limit = int(request.args.get("limit", 200))
        result = normalizar_pendientes(limit=limit)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
