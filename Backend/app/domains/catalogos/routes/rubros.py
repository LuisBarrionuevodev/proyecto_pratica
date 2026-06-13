"""Catálogo de rubros (STAB-8)."""

from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.catalogos.schemas.rubros_in import RubrosCatalogIn
from app.domains.catalogos.services.rubros_catalog_service import listar_rubros_catalogo

from . import catalogos


@catalogos.get("/rubros")
def listar_rubros_route():
    """
    Catálogo liviano de rubros desde DB.

    Query: ``q`` (opcional), ``limit`` (default 500, máx. 500).

    Retorno: ``{ "items": [ { id, nombre, activo } ] }``
    """
    raw = request.args.to_dict()
    try:
        params = RubrosCatalogIn.model_validate(
            {
                "q": raw.get("q"),
                "limit": int(raw["limit"]) if raw.get("limit") else 500,
            }
        )
        items = listar_rubros_catalogo(q=params.q, limit=params.limit)
        return jsonify({"items": items}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": e.errors()}), 422
