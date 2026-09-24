from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.indicadores.schemas.indicadores_filtros_query import IndicadoresFiltrosQuery
from app.domains.indicadores.utils.indicadores_perf_log import PerfTimer, log_indicadores_endpoint
from app.shared.errors import pydantic_errors_to_cell_map

T = TypeVar("T")


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


def build_indicadores_with_perf(
    endpoint: str,
    q: IndicadoresFiltrosQuery,
    builder: Callable[..., T],
) -> T:
    """
    Ejecuta un builder de indicadores y emite log de performance del endpoint.

    Parámetros:
        endpoint: clave corta (ej. ``ejecutivo``, ``productividad``).
        q: filtros validados.
        builder: función ``build_indicadores_*``.

    Retorno:
        Salida Pydantic del builder (sin cambios de negocio).
    """
    timer = PerfTimer()
    out = builder(
        desde=q.desde,
        hasta=q.hasta,
        distrito_id=q.distrito_id,
        inspector_id=q.inspector_id,
    )
    log_indicadores_endpoint(
        endpoint,
        total_ms=timer.elapsed_ms(),
        desde=q.desde,
        hasta=q.hasta,
        distrito_id=q.distrito_id,
        inspector_id=q.inspector_id,
    )
    return out
