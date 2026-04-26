from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.schemas.completar_trabajo_pendientes_resumen_filters import (
    CompletarTrabajoPendientesResumenQuery,
)
from app.domains.actuaciones.services.completar_trabajo_pendientes_resumen_service import (
    list_completar_trabajo_pendientes_resumen_por_dia,
)

from . import actuacion


@actuacion.get("/completar-trabajo/pendientes/resumen")
def resumen_completar_trabajo_pendientes_por_dia():
    """
    Resumen de pendientes Completar trabajo por día de ruta publicada (agregado en servidor).

    Query:
        - fecha_desde: YYYY-MM-DD (obligatorio)
        - fecha_hasta: YYYY-MM-DD (obligatorio)
        Rango máximo: 120 días. `fecha_desde` <= `fecha_hasta`.

    Returns:
        { "dias": [ ... ], "meta": { fecha_desde, fecha_hasta, hoy } }

    Cada elemento de `dias` incluye al menos: `fecha`, `total` (pendientes EN_PROCESO),
    `atrasado`, `items_con_actuacion`, `hubo_actividad`, `sin_pendientes_cierre`,
    `categoria_calendario` (`CON_PENDIENTES` | `COMPLETO`).

    Incluye días con **actividad** en el módulo (ítem con actuación en ruta publicada), aunque
    `total` sea 0 (sin cierres pendientes). Fechas sin fila = sin actividad en el rango.

    Errors:
        422: validación Pydantic
    """
    try:
        raw = request.args.to_dict()
        params = {k: (v if v else None) for k, v in raw.items()}
        filters = CompletarTrabajoPendientesResumenQuery.model_validate(params)
        dias, meta = list_completar_trabajo_pendientes_resumen_por_dia(
            fecha_desde=filters.fecha_desde,
            fecha_hasta=filters.fecha_hasta,
        )
        return jsonify({"dias": dias, "meta": meta}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": e.errors()}), 422
