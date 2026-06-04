from __future__ import annotations

from flask import jsonify

from . import indicadores_api
from ._common import parse_indicadores_filtros_query
from app.domains.indicadores.services.indicadores_resumen_service import (
    build_indicadores_resumen,
)


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
    q, err = parse_indicadores_filtros_query()
    if err is not None:
        return err

    out = build_indicadores_resumen(
        desde=q.desde,
        hasta=q.hasta,
        distrito_id=q.distrito_id,
        inspector_id=q.inspector_id,
    )
    return jsonify(out.to_json_response()), 200
