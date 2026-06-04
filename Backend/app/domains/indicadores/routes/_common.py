from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.indicadores.schemas.indicadores_filtros_query import IndicadoresFiltrosQuery
from app.shared.errors import pydantic_errors_to_cell_map


def query_dict_from_request() -> dict:
    """Arma dict para Pydantic desde query string (GET indicadores)."""
    args = request.args
    raw: dict = {
        "desde": args.get("desde"),
        "hasta": args.get("hasta"),
    }
    if args.get("distrito_id") not in (None, ""):
        raw["distrito_id"] = args.get("distrito_id")
    if args.get("inspector_id") not in (None, ""):
        raw["inspector_id"] = args.get("inspector_id")
    return raw


def parse_indicadores_filtros_query():
    """
    Valida query params compartidos (desde, hasta, distrito_id?, inspector_id?).

    Retorno:
        Tupla (IndicadoresFiltrosQuery, None) o (None, response_422).
    """
    try:
        return IndicadoresFiltrosQuery.model_validate(query_dict_from_request()), None
    except ValidationError as e:
        return None, (
            jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}),
            422,
        )
