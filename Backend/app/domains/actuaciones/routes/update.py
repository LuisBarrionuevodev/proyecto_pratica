from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.schemas.actuacion_patch_in import ActuacionPatchIn
from app.shared.errors import pydantic_errors_to_cell_map
from app.domains.actuaciones.services.update_service import actualizar_actuacion as actualizar_actuacion_service
from app.domains.actuaciones.services.patch_service import actualizar_actuacion_parcial

from . import actuacion


@actuacion.put("/<int:actuacion_id>")
def actualizar_actuacion_route(actuacion_id: int):
    """Actualiza una actuación existente desde una fila del grid (requiere payload completo)."""
    data: Dict[str, Any] = request.get_json(silent=True) or {}

    try:
        data["id"] = actuacion_id

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


@actuacion.patch("/<int:actuacion_id>")
def actualizar_actuacion_parcial_route(actuacion_id: int):
    """
    Actualiza campos específicos de una actuación (PATCH).
    Solo actualiza los campos que se envíen.
    Ideal para ediciones desde Material React Table.
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}

    try:
        patch = ActuacionPatchIn.model_validate(data)
        act = actualizar_actuacion_parcial(actuacion_id, patch)
        return jsonify(actuacion_to_grid_row(act)), 200

    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": e.errors()}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
