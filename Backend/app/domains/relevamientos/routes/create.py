from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.relevamientos.mappers.grid.relevamiento_row_mapper import map_relevamiento_row
from app.domains.relevamientos.presenters.relevamiento_presenter import relevamiento_to_row
from app.domains.relevamientos.schemas.grid.relevamiento_row_in import RelevamientoGridRowIn
from app.shared.errors import pydantic_errors_to_cell_map
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.geolocalizacion.geocode.services.pipeline_service import (
    pipeline_post_commit,
)

from . import relevamiento


@relevamiento.post("/")
def crear_relevamiento():
    """
    Crea un relevamiento desde una fila del grid.
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}

    try:
        row = RelevamientoGridRowIn.model_validate(data)
        payload = map_relevamiento_row(row)
        rel = crear_relevamiento_desde_payload(payload)
        try:
            if rel.domicilio_id:
                pipeline_post_commit(int(rel.domicilio_id))
        except Exception:
            pass
        return jsonify(relevamiento_to_row(rel)), 201
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
