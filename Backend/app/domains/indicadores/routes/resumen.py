from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from . import indicadores_api
from app.domains.indicadores.schemas.resumen_query import IndicadoresResumenQuery
from app.domains.indicadores.services.indicadores_resumen_service import (
    build_indicadores_resumen,
)
from app.shared.errors import pydantic_errors_to_cell_map


def _query_dict_from_request() -> dict:
    """Arma dict para Pydantic desde query string (GET)."""
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


@indicadores_api.get("/resumen")
def get_indicadores_resumen():
    """
    Resumen agregado para dashboard operativo (actuaciones, actas, contraproducencias, mapa operativo).

    Qué hace: valida query params, calcula agregados en lectura (sin commit).

    Parámetros:
        Query: desde, hasta (YYYY-MM-DD); opcional distrito_id, inspector_id.

    Retorno:
        200 JSON `IndicadoresResumenOut` (incluye `mapa_operativo` alineado a D1); 422 si validación falla.

    Errores:
        401 si falta JWT (guard global).
        422 ValidationError → mapa de errores por campo.
    """
    try:
        q = IndicadoresResumenQuery.model_validate(_query_dict_from_request())
    except ValidationError as e:
        return (
            jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}),
            422,
        )

    out = build_indicadores_resumen(
        desde=q.desde,
        hasta=q.hasta,
        distrito_id=q.distrito_id,
        inspector_id=q.inspector_id,
    )
    return jsonify(out.to_json_response()), 200
