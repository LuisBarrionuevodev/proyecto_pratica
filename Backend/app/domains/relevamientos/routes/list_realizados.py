from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters
from app.domains.relevamientos.services.list_service import (
    listar_relevamientos_realizados_actuacion_completada_con_filtros,
)
from app.domains.relevamientos.presenters.relevamiento_presenter import relevamiento_to_row

from . import relevamiento


@relevamiento.get("/realizados")
def listar_relevamientos_realizados():
    """
    Relevamientos con actuación completada vía flujo de ruta (iniciador RELEVAMIENTO en CUMPLIDO con actuación).
    """
    try:
        raw_params = request.args.to_dict()
        params = {k: (v if v else None) for k, v in raw_params.items()}
        if "page" in params and params["page"]:
            params["page"] = int(params["page"])
        if "page_size" in params and params["page_size"]:
            params["page_size"] = int(params["page_size"])

        filters = RelevamientosListFilters.model_validate(params)
        result = listar_relevamientos_realizados_actuacion_completada_con_filtros(filters)
        items_dto = [relevamiento_to_row(rel) for rel in result["items"]]
        return jsonify({"items": items_dto, "meta": result["meta"]}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": e.errors()}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
