from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.schemas.grid.errors import pydantic_errors_to_cell_map
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload

from . import actuacion


@actuacion.post("/")
def crear_actuacion():
    """Crea una actuación desde una fila del grid."""
    data: Dict[str, Any] = request.get_json(silent=True) or {}

    try:
        row = ActuacionGridRowIn.model_validate(data)
        payload = map_actuacion_row(row)

        act = crear_actuacion_desde_payload(payload)
        return jsonify(actuacion_to_grid_row(act)), 201

    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422

    except ValueError as e:
        return jsonify({"detail": str(e)}), 400

    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500

