from __future__ import annotations

from flask import jsonify

from . import indicadores_api
from ._common import build_indicadores_with_perf, parse_indicadores_filtros_query
from app.domains.indicadores.services.indicadores_riesgo_service import (
    build_indicadores_riesgo,
)


@indicadores_api.get("/riesgo")
def get_indicadores_riesgo():
    """
    Indicadores de riesgo bromatológico (rubros, motivos, decomiso por rubro).

    Query: desde, hasta; opcional distrito_id, inspector_id.
    Retorno: 200 JSON ``IndicadoresRiesgoOut``.
    """
    q, err = parse_indicadores_filtros_query()
    if err is not None:
        return err

    out = build_indicadores_with_perf("riesgo", q, build_indicadores_riesgo)
    return jsonify(out.to_json_response()), 200
