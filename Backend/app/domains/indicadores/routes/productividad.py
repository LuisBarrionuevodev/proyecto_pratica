from __future__ import annotations

from flask import jsonify

from . import indicadores_api
from ._common import build_indicadores_with_perf, parse_indicadores_filtros_query
from app.domains.indicadores.services.indicadores_productividad_service import (
    build_indicadores_productividad,
)


@indicadores_api.get("/productividad")
def get_indicadores_productividad():
    """
    Productividad por inspector (realizadas, no realizadas, actas labradas).

    Query: desde, hasta; opcional distrito_id, inspector_id.
    Retorno: 200 JSON ``IndicadoresProductividadOut``.
    """
    q, err = parse_indicadores_filtros_query()
    if err is not None:
        return err

    out = build_indicadores_with_perf("productividad", q, build_indicadores_productividad)
    return jsonify(out.to_json_response()), 200
