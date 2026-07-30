"""
API de consulta histórica por DNI/CUIT (Establecimientos — solo lectura).
"""

from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, request

from app.domains.establecimientos.presenters.historial_contribuyente_presenters import (
    historial_contribuyente_rows,
)
from app.domains.establecimientos.services.historial_contribuyente_service import (
    list_historial_por_documento,
)

establecimientos_bp = Blueprint("establecimientos", __name__)

_MAX_LIMIT = 100


def _int_param(name: str, default: int, *, min_v: int = 1, max_v: int | None = None) -> int:
    raw = request.args.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        v = int(raw)
    except ValueError:
        return default
    if v < min_v:
        return min_v
    if max_v is not None and v > max_v:
        return max_v
    return v


def _parse_date(name: str) -> date | None:
    raw = request.args.get(name)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return date.fromisoformat(str(raw).strip())
    except ValueError:
        return None


@establecimientos_bp.get("/historial-contribuyente")
def historial_contribuyente_route():
    """
    Historial completo de un contribuyente por DNI/CUIT.

    Query:
        documento (requerido): DNI/CUIT con o sin separadores.
        desde, hasta: filtro opcional ISO (YYYY-MM-DD).
        page (default 1), limit (default 20, max 100).

    Retorno:
        ``{ "rows": [...], "meta": { "total", "page", "limit", "documento_normalizado" } }``
    """
    documento = request.args.get("documento")
    if documento is None or not str(documento).strip():
        return jsonify({"detail": "El parámetro 'documento' es requerido."}), 400

    page = _int_param("page", 1, min_v=1)
    limit = _int_param("limit", 20, min_v=1, max_v=_MAX_LIMIT)
    desde = _parse_date("desde")
    hasta = _parse_date("hasta")

    entries, total, norm = list_historial_por_documento(
        documento,
        desde=desde,
        hasta=hasta,
        page=page,
        limit=limit,
    )
    rows = historial_contribuyente_rows(entries)

    return (
        jsonify(
            {
                "rows": rows,
                "meta": {
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "documento_normalizado": norm,
                },
            }
        ),
        200,
    )
