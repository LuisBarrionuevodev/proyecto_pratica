from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.schemas.list_filters import ActuacionesListFilters
from app.domains.actuaciones.services.list_service import listar_actuaciones_con_filtros
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_grid_row,
    build_actuacion_grid_batch_maps,
    build_iniciador_ruta_por_actuacion_id,
)
from app.domains.actuaciones.services.actuacion_reencolado_service import (
    build_actuacion_editable_flags_por_actuacion_id,
)

from . import actuacion


@actuacion.get("/")
def listar_actuaciones():
    """
    Lista actuaciones con filtros opcionales.
    
    Query params:
        - desde: YYYY-MM-DD (opcional, default: primer día del mes corriente)
        - hasta: YYYY-MM-DD (opcional, default: último día del mes corriente)
        - tipo: INSPECCION|REINSPECCION|etc (opcional)
        - contraproducencia: LOCAL CERRADO|CLIMA|etc (opcional)
        - orden_trabajo: número de OT (opcional, búsqueda exacta)
        - page: número de página (default: 1)
        - page_size: tamaño de página (default: 50)
    
    Returns:
        {
            "items": [...],
            "meta": {
                "total": 123,
                "page": 1,
                "page_size": 50,
                "desde": "2025-01-01",
                "hasta": "2025-01-31",
                ...
            }
        }
    
    Errors:
        - 400: Parámetros inválidos o orden_trabajo no encontrada
        - 422: Error de validación Pydantic
    """
    try:
        # Construir dict de query params (convertir a None si vacío)
        raw_params = request.args.to_dict()
        params = {k: (v if v else None) for k, v in raw_params.items()}
        
        # Convertir page/page_size a int si existen
        if "page" in params and params["page"]:
            params["page"] = int(params["page"])
        if "page_size" in params and params["page_size"]:
            params["page_size"] = int(params["page_size"])
        if "actuacion_id" in params and params["actuacion_id"]:
            params["actuacion_id"] = int(params["actuacion_id"])
        
        # Validar con Pydantic
        filters = ActuacionesListFilters.model_validate(params)
        
        # Ejecutar query
        result = listar_actuaciones_con_filtros(filters)
        
        # Transformar items con presenter grid completo (todas las columnas)
        items_raw = result["items"]
        counts_by_eo = build_counts_by_eo_from_actuaciones(items_raw)
        act_ids = [int(a.id) for a in items_raw]
        iniciador_map = build_iniciador_ruta_por_actuacion_id(act_ids)
        batch = build_actuacion_grid_batch_maps(items_raw, iniciador_map)
        editable_map = build_actuacion_editable_flags_por_actuacion_id(act_ids)
        items_dto = [
            actuacion_to_grid_row(
                act,
                counts_by_eo=counts_by_eo,
                iniciador_desde_ruta=iniciador_map.get(int(act.id)),
                batch=batch,
                editable_override=editable_map.get(int(act.id)),
            )
            for act in items_raw
        ]
        
        return jsonify({
            "items": items_dto,
            "meta": result["meta"]
        }), 200
    
    except ValidationError as e:
        return jsonify({
            "detail": "Validation error",
            "errors": e.errors()
        }), 422
    
    except ValueError as e:
        # Orden de trabajo no encontrada
        return jsonify({"detail": str(e)}), 400
    
    except Exception as e:
        return jsonify({
            "detail": "Error interno",
            "error": str(e)
        }), 500

