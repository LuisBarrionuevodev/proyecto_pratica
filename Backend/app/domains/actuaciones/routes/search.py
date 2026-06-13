"""Búsqueda liviana de actuaciones y órdenes (STAB-6)."""

from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.schemas.search_in import ActuacionesSearchIn, OrdenesSearchIn
from app.domains.actuaciones.services.search_service import (
    buscar_actuaciones_liviano,
    buscar_ordenes_liviano,
)

from . import actuacion


@actuacion.get("/search")
def buscar_actuaciones_route():
    """
    Búsqueda global liviana (Autocomplete).

    Query: ``q`` (mín. 2 caracteres), ``limit`` (default 20, máx. 50).

    Retorno: ``{ "items": [ { id, label, orden_trabajo_numero, ... } ] }``
    """
    raw = request.args.to_dict()
    try:
        params = ActuacionesSearchIn.model_validate(
            {
                "q": raw.get("q") or "",
                "limit": int(raw["limit"]) if raw.get("limit") else 20,
            }
        )
        items = buscar_actuaciones_liviano(params.q, limit=params.limit)
        return jsonify({"items": items}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": e.errors()}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400


@actuacion.get("/ordenes/search")
def buscar_ordenes_route():
    """
    Búsqueda de órdenes de trabajo por número (Autocomplete).

    Query: ``q``, ``limit`` (default 20).
    """
    raw = request.args.to_dict()
    try:
        params = OrdenesSearchIn.model_validate(
            {
                "q": raw.get("q") or "",
                "limit": int(raw["limit"]) if raw.get("limit") else 20,
            }
        )
        items = buscar_ordenes_liviano(params.q, limit=params.limit)
        return jsonify({"items": items}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": e.errors()}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
