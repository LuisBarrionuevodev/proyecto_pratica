from __future__ import annotations

from flask import jsonify

from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio,
)

from . import geolocalizacion_calles


@geolocalizacion_calles.post("/geolocalizacion/calles/normalize/<int:domicilio_id>")
def normalize_one(domicilio_id: int):
    """
    Normaliza un domicilio específico.
    """
    try:
        result = normalizar_domicilio(domicilio_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e), "domicilio_id": domicilio_id}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "domicilio_id": domicilio_id}), 500
