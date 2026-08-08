from __future__ import annotations

from flask import jsonify

from . import indicadores_api
from ._common import build_indicadores_with_perf, parse_indicadores_filtros_query
from app.domains.indicadores.services.indicadores_ejecutivo_service import (
    build_indicadores_ejecutivo,
)


@indicadores_api.get("/ejecutivo")
def get_indicadores_ejecutivo():
    """
    KPIs del resumen ejecutivo del dashboard (realizadas + actas labradas).

    Query: desde, hasta (YYYY-MM-DD); opcional distrito_id, inspector_id.
    Retorno: 200 JSON ``IndicadoresEjecutivoOut``; 422 si validación falla.
    """
    q, err = parse_indicadores_filtros_query()
    if err is not None:
        return err

    out = build_indicadores_with_perf("ejecutivo", q, build_indicadores_ejecutivo)
    return jsonify(out.to_json_response()), 200
