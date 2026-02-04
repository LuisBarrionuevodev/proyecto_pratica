from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request

from app.domains.geolocalizacion.normalizacion_calles.services.set_numero_service import (
    set_numero_esquina,
)

from . import geolocalizacion_calles


@geolocalizacion_calles.post("/geolocalizacion/calles/set-numero/<int:domicilio_id>")
def set_numero_route(domicilio_id: int):
    """
    Setea el número/esquina de un domicilio y re-normaliza.
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    numero = data.get("numero")
    numero_tipo = data.get("numero_tipo")
    if not numero:
        return jsonify({"detail": "numero es obligatorio"}), 400
    try:
        result = set_numero_esquina(domicilio_id, str(numero), numero_tipo)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
