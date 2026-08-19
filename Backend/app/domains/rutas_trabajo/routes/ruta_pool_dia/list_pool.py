from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.rutas_trabajo.routes.ruta_pool_dia import ruta_pool_dia
from app.domains.rutas_trabajo.schemas.ruta_pool_dia_in import RutaPoolDiaListQuery
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import (
    list_ruta_pool_dia,
    ruta_pool_dia_row_dict,
)
from app.shared.errors import pydantic_errors_to_cell_map


@ruta_pool_dia.get("")
@ruta_pool_dia.get("/")
def list_pool():
    """
    Lista paginada del pool del día.

    Query params: fecha (obligatorio), turno_id, distrito_id, rubro_id, ruta_trabajo_id, estado, q, page, per_page.
    """
    try:
        payload = RutaPoolDiaListQuery.model_validate(request.args.to_dict(flat=True))
        items, total = list_ruta_pool_dia(
            fecha=payload.fecha,
            turno_id=payload.turno_id,
            distrito_id=payload.distrito_id,
            rubro_id=payload.rubro_id,
            ruta_trabajo_id=payload.ruta_trabajo_id,
            estado=payload.estado,
            q=payload.q,
            page=payload.page,
            per_page=payload.per_page,
        )
        return jsonify(
            {
                "items": [ruta_pool_dia_row_dict(row) for row in items],
                "meta": {
                    "total": total,
                    "page": payload.page,
                    "per_page": payload.per_page,
                },
            }
        ), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
