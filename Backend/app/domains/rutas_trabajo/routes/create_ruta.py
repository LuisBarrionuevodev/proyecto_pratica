from __future__ import annotations

from typing import Any

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.rutas_trabajo.presenters.ruta_presenters import ruta_trabajo_to_dict
from app.domains.rutas_trabajo.schemas.ruta_create_in import RutaTrabajoCreateIn
from app.domains.rutas_trabajo.services.ruta_create_service import create_ruta_trabajo
from app.shared.errors import pydantic_errors_to_cell_map

from . import rutas_trabajo


@rutas_trabajo.post("")
@rutas_trabajo.post("/")
def create_ruta():
    """
    Crea una ruta de trabajo en estado BORRADOR.
    """
    data: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        payload = RutaTrabajoCreateIn.model_validate(data)
        ruta = create_ruta_trabajo(
            fecha=payload.fecha,
            turno=payload.turno,
            observaciones=payload.observaciones,
        )
        return jsonify({"item": ruta_trabajo_to_dict(ruta)}), 201
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
