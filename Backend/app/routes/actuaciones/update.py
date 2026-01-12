from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from pydantic import ValidationError

from app.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.presenters.actuacion_presenters import actuacion_to_grid_row
from app.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.schemas.grid.errors import pydantic_errors_to_cell_map
from app.services.actuaciones.update_service import actualizar_actuacion as actualizar_actuacion_service

from . import actuacion


@actuacion.put("/<int:actuacion_id>")
def actualizar_actuacion_route(actuacion_id: int):
    """Actualiza una actuación existente desde una fila del grid."""
    data: Dict[str, Any] = request.get_json(silent=True) or {}

    try:
        data["id"] = actuacion_id  # ok si tu schema lo acepta

        row = ActuacionGridRowIn.model_validate(data)
        payload = map_actuacion_row(row)

        act = actualizar_actuacion_service(actuacion_id, payload)
        return jsonify(actuacion_to_grid_row(act)), 200

    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500

