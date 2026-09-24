from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.relevamientos.schemas.pendientes_filters import RelevamientosPendientesFilters
from app.domains.relevamientos.services.pendientes_service import (
    get_pendientes_summary,
    get_pendientes_list,
)
from app.domains.relevamientos.presenters.relevamiento_presenter import (
    relevamiento_to_pendiente_domicilio_row,
)
from app.shared.errors import pydantic_errors_to_cell_map

from . import relevamiento


@relevamiento.get("/pendientes/summary")
def pendientes_summary():
    """
    Resumen de pendientes de Relevamientos.
    """
    try:
        params = {k: (v if v else None) for k, v in request.args.to_dict().items()}
        filters = RelevamientosPendientesFilters.model_validate(params)
        return jsonify(get_pendientes_summary(filters)), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500


@relevamiento.get("/pendientes")
def pendientes_list():
    """
    Lista pendientes de Relevamientos por tipo.
    """
    try:
        params = {k: (v if v else None) for k, v in request.args.to_dict().items()}
        filters = RelevamientosPendientesFilters.model_validate(params)
        if not filters.tipo:
            return jsonify({"detail": "tipo es obligatorio."}), 400
        rels = get_pendientes_list(filters)
        return jsonify([relevamiento_to_pendiente_domicilio_row(r) for r in rels]), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
