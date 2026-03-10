from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.relevamientos.mappers.grid.relevamiento_row_mapper import map_relevamiento_row
from app.domains.relevamientos.presenters.relevamiento_presenter import relevamiento_to_row
from app.domains.relevamientos.schemas.grid.relevamiento_row_in import RelevamientoGridRowIn
from app.shared.errors import pydantic_errors_to_cell_map
from app.domains.relevamientos.services.update_service import actualizar_relevamiento
from app.domains.relevamientos.services.operational_guard_service import RelevamientoNoOperativoError

from . import relevamiento


@relevamiento.put("/<int:relevamiento_id>")
def actualizar_relevamiento_route(relevamiento_id: int):
    """
    Actualiza un relevamiento existente desde una fila del grid (payload completo).
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}

    try:
        data["id"] = relevamiento_id
        row = RelevamientoGridRowIn.model_validate(data)
        payload = map_relevamiento_row(row)
        rel = actualizar_relevamiento(relevamiento_id, payload)
        return jsonify(relevamiento_to_row(rel)), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except RelevamientoNoOperativoError as e:
        return jsonify({"detail": str(e)}), 409
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
