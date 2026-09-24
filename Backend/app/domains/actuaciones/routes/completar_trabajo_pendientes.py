from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.schemas.completar_trabajo_list_filters import CompletarTrabajoPendientesListFilters
from app.domains.actuaciones.services.completar_trabajo_pendientes_list_service import (
    list_completar_trabajo_pendientes,
)

from . import actuacion


@actuacion.get("/completar-trabajo/pendientes")
def listar_completar_trabajo_pendientes():
    """
    Lista trabajos pendientes de completar para el día operativo de la ruta (`RutaTrabajo.fecha`):
    ruta PUBLICADA e ítems EN_PROCESO (solo existen tras publicar).

    Query:
        - fecha: YYYY-MM-DD (obligatorio)
        - page: default 1
        - per_page: default 20, máx 50

    Returns:
        { "items": [...], "meta": { total, page, per_page, fecha } }

    Errors:
        422: validación Pydantic
    """
    try:
        raw = request.args.to_dict()
        params = {k: (v if v else None) for k, v in raw.items()}
        if params.get("page"):
            params["page"] = int(params["page"])
        if params.get("per_page"):
            params["per_page"] = int(params["per_page"])
        filters = CompletarTrabajoPendientesListFilters.model_validate(params)
        items, meta = list_completar_trabajo_pendientes(
            fecha=filters.fecha,
            page=filters.page,
            per_page=filters.per_page,
        )
        return jsonify({"items": items, "meta": meta}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": e.errors()}), 422
