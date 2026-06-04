from __future__ import annotations

from flask import jsonify

from . import indicadores_api
from ._common import parse_indicadores_filtros_query
from app.domains.indicadores.services.indicadores_pendientes_service import (
    build_indicadores_pendientes,
)


@indicadores_api.get("/pendientes")
def get_indicadores_pendientes():
    """
    Pendientes operativos por tipo de iniciador y tabla por distrito.

    Query: desde, hasta; opcional distrito_id, inspector_id.
    Retorno: 200 JSON ``IndicadoresPendientesOut``.
    """
    q, err = parse_indicadores_filtros_query()
    if err is not None:
        return err

    out = build_indicadores_pendientes(
        desde=q.desde,
        hasta=q.hasta,
        distrito_id=q.distrito_id,
        inspector_id=q.inspector_id,
    )
    return jsonify(out.to_json_response()), 200
