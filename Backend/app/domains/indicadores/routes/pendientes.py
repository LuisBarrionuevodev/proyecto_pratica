from __future__ import annotations

from flask import jsonify

from . import indicadores_api
from ._common import build_indicadores_with_perf, parse_indicadores_filtros_query
from app.domains.indicadores.services.indicadores_pendientes_service import (
    build_indicadores_pendientes,
)


@indicadores_api.get("/pendientes")
def get_indicadores_pendientes():
    """
    Pendientes operativos por tipo de iniciador y tabla por distrito (stock actual).

    Query: desde, hasta (ignorados en conteo); opcional distrito_id. inspector_id ignorado.
    Retorno: 200 JSON ``IndicadoresPendientesOut``.
    """
    q, err = parse_indicadores_filtros_query()
    if err is not None:
        return err

    out = build_indicadores_with_perf("pendientes", q, build_indicadores_pendientes)
    return jsonify(out.to_json_response()), 200
