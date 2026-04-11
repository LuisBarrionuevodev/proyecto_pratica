"""
API lectura: fichas ``establecimiento_operativo`` (listado, detalle, historial de actuaciones).
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.models import EstablecimientoOperativo
from app.domains.establecimientos.presenters.establecimiento_operativo_presenters import (
    actuacion_historial_row,
    establecimiento_operativo_detail,
    establecimiento_operativo_list_row,
)
from app.domains.establecimientos.services.get_establecimiento_operativo_service import (
    get_establecimiento_operativo_con_metricas,
)
from app.domains.establecimientos.services.historial_actuaciones_establecimiento_service import (
    list_actuaciones_por_establecimiento_operativo,
)
from app.domains.establecimientos.services.list_establecimientos_operativos_service import (
    list_establecimientos_operativos,
)

establecimientos_operativos_bp = Blueprint("establecimientos_operativos", __name__)

_MAX_PAGE_SIZE = 100


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


def _optional_int(name: str) -> int | None:
    raw = request.args.get(name)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


@establecimientos_operativos_bp.get("")
def list_establecimientos_operativos_route():
    """
    Lista paginada de fichas operativas.

    Query:
        page, page_size (default 20, max 100)
        calle: subcadena en calle del domicilio
        contrib: subcadena en datos del contribuyente
        distrito_id, rubro_id: filtros exactos opcionales
    """
    page = _int_param("page", 1, min_v=1)
    page_size = _int_param("page_size", 20, min_v=1, max_v=_MAX_PAGE_SIZE)
    calle = request.args.get("calle")
    contrib = request.args.get("contrib")
    distrito_id = _optional_int("distrito_id")
    rubro_id = _optional_int("rubro_id")

    items, total = list_establecimientos_operativos(
        page=page,
        page_size=page_size,
        calle=calle,
        contrib=contrib,
        distrito_id=distrito_id,
        rubro_id=rubro_id,
    )
    rows = [establecimiento_operativo_list_row(eo) for eo in items]
    return (
        jsonify(
            {
                "items": rows,
                "meta": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                },
            }
        ),
        200,
    )


@establecimientos_operativos_bp.get("/<int:establecimiento_id>")
def get_establecimiento_operativo_route(establecimiento_id: int):
    """
    Detalle de una ficha + conteo de actuaciones y última fecha de actuación.
    """
    eo, cnt, ultima = get_establecimiento_operativo_con_metricas(establecimiento_id)
    if eo is None:
        return jsonify({"detail": "Establecimiento operativo no encontrado."}), 404

    payload = establecimiento_operativo_detail(eo, actuaciones_count=cnt, ultima_actuacion_fecha=ultima)
    return jsonify(payload), 200


@establecimientos_operativos_bp.get("/<int:establecimiento_id>/actuaciones")
def list_actuaciones_establecimiento_route(establecimiento_id: int):
    """
    Historial de actuaciones vinculadas a la ficha (paginado).
    """
    if EstablecimientoOperativo.query.filter_by(id=establecimiento_id).first() is None:
        return jsonify({"detail": "Establecimiento operativo no encontrado."}), 404

    page = _int_param("page", 1, min_v=1)
    page_size = _int_param("page_size", 20, min_v=1, max_v=_MAX_PAGE_SIZE)

    acts, total = list_actuaciones_por_establecimiento_operativo(
        establecimiento_id,
        page=page,
        page_size=page_size,
    )
    rows = [actuacion_historial_row(a) for a in acts]
    return (
        jsonify(
            {
                "items": rows,
                "meta": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "establecimiento_operativo_id": establecimiento_id,
                },
            }
        ),
        200,
    )
