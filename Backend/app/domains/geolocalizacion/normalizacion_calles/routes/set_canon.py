from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request

from app.domains.geolocalizacion.normalizacion_calles.services.set_calle_canon_service import (
    set_calle_canon,
)

from . import geolocalizacion_calles


@geolocalizacion_calles.post("/geolocalizacion/calles/set-canon/<int:domicilio_id>")
def set_calle_canon_route(domicilio_id: int):
    """
    Setea la calle canónica de un domicilio.
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    calle_catalogo_id = data.get("calle_catalogo_id")
    if not calle_catalogo_id:
        return jsonify({"detail": "calle_catalogo_id es obligatorio"}), 400
    try:
        result = set_calle_canon(domicilio_id, int(calle_catalogo_id))
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
