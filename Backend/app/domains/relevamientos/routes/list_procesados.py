from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters
from app.domains.relevamientos.services.list_service import listar_relevamientos_procesados_con_filtros
from app.shared.errors import pydantic_errors_to_cell_map

from . import relevamiento


@relevamiento.get("/procesados")
def listar_relevamientos_procesados():
    """
    Bandeja Procesados: cierres terminales vía ``iniciador_ruta`` (no solo CUMPLIDO).
    """
    try:
        raw_params = request.args.to_dict()
        params = {k: (v if v else None) for k, v in raw_params.items()}
        if "page" in params and params["page"]:
            params["page"] = int(params["page"])
        if "page_size" in params and params["page_size"]:
            params["page_size"] = int(params["page_size"])

        filters = RelevamientosListFilters.model_validate(params)
        result = listar_relevamientos_procesados_con_filtros(filters)
        return jsonify({"items": result["items"], "meta": result["meta"]}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
