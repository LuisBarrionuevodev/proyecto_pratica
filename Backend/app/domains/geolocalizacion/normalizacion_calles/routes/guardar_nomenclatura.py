from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.geolocalizacion.normalizacion_calles.schemas.guardar_nomenclatura_in import (
    GuardarNomenclaturaIn,
)
from app.domains.geolocalizacion.normalizacion_calles.services.guardar_nomenclatura_service import (
    guardar_nomenclatura_hibrida,
)

from . import geolocalizacion_calles


@geolocalizacion_calles.post("/geolocalizacion/calles/guardar-nomenclatura/<int:domicilio_id>")
def guardar_nomenclatura_route(domicilio_id: int):
    """
    Guarda nomenclatura híbrida (calle y esquina en modo catálogo o manual) en una sola operación.

    Qué hace:
        Valida el cuerpo con ``GuardarNomenclaturaIn``, orquesta persistencia y geocode.

    Parámetros:
        domicilio_id: id del domicilio en la URL.

    Retorno:
        JSON 200 con resumen; 422 si validación Pydantic; 400 si ``ValueError`` de negocio.

    Errores:
        ValidationError → 422 con detalle.
        ValueError → 400.
    """
    raw: Dict[str, Any] = request.get_json(silent=True) or {}
    try:
        data = GuardarNomenclaturaIn.model_validate(raw)
    except ValidationError as e:
        errs = []
        for err in e.errors():
            item = {k: v for k, v in err.items() if k != "ctx"}
            errs.append(item)
        return jsonify({"detail": errs}), 422
    try:
        result = guardar_nomenclatura_hibrida(domicilio_id, data)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
