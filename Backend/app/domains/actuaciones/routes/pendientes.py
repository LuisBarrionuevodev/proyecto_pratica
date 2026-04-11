from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.pendientes_service import (
    get_pendientes_summary,
    get_pendientes_list,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_grid_row,
    actuacion_to_pendiente_domicilio_row,
)
from app.shared.errors import pydantic_errors_to_cell_map

from . import actuacion


@actuacion.get("/pendientes/summary")
def pendientes_summary():
    """
    Resumen de pendientes de Actuaciones.
    """
    try:
        params = {k: (v if v else None) for k, v in request.args.to_dict().items()}
        filters = ActuacionesPendientesFilters.model_validate(params)
        return jsonify(get_pendientes_summary(filters)), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500


@actuacion.get("/pendientes")
def pendientes_list():
    """
    Lista pendientes de Actuaciones por tipo.
    """
    try:
        params = {k: (v if v else None) for k, v in request.args.to_dict().items()}
        filters = ActuacionesPendientesFilters.model_validate(params)
        if not filters.tipo:
            return jsonify({"detail": "tipo es obligatorio."}), 400
        acts = get_pendientes_list(filters)
        if filters.tipo == "domicilios":
            return jsonify([actuacion_to_pendiente_domicilio_row(a) for a in acts]), 200
        counts_by_eo = build_counts_by_eo_from_actuaciones(acts)
        return jsonify([actuacion_to_grid_row(a, counts_by_eo=counts_by_eo) for a in acts]), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
