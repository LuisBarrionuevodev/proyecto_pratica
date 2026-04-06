"""
Planificación MVP — métricas, carga territorial, urgentes, pendientes por distrito.
"""

from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.rutas_trabajo.presenters.ruta_presenters import iniciador_pendiente_to_row
from app.domains.rutas_trabajo.schemas.planificacion_in import (
    PlanificacionMetricasQuery,
    PlanificacionPendientesContextoQuery,
    PlanificacionUrgentesQuery,
)
from app.domains.rutas_trabajo.services.planificacion_service import (
    get_carga_por_distritos,
    get_planificacion_metricas,
    get_planificacion_pendientes_contexto,
    get_planificacion_urgentes,
)
from app.shared.errors import pydantic_errors_to_cell_map

from . import rutas_trabajo


@rutas_trabajo.get("/<int:ruta_id>/planificacion/metricas")
def planificacion_metricas(ruta_id: int):
    """M1: cards / KPIs."""
    params = {k: (v if v != "" else None) for k, v in request.args.to_dict().items()}
    try:
        q = PlanificacionMetricasQuery.model_validate(params)
        data = get_planificacion_metricas(ruta_id, q.distrito_id)
        return jsonify(data), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409


@rutas_trabajo.get("/<int:ruta_id>/planificacion/carga-distritos")
def planificacion_carga_distritos(ruta_id: int):
    """M2: conteos por distrito para mapa."""
    try:
        items = get_carga_por_distritos(ruta_id)
        return jsonify({"items": items}), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409


@rutas_trabajo.get("/<int:ruta_id>/planificacion/urgentes")
def planificacion_urgentes(ruta_id: int):
    """M3: bandeja urgentes (elegible_urgente)."""
    params = {k: (v if v != "" else None) for k, v in request.args.to_dict().items()}
    try:
        q = PlanificacionUrgentesQuery.model_validate(params)
        rows, total = get_planificacion_urgentes(
            ruta_id, page=q.page, per_page=q.per_page
        )
        return jsonify(
            {
                "items": [iniciador_pendiente_to_row(row) for row in rows],
                "meta": {"total": total, "page": q.page, "per_page": q.per_page},
            }
        ), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409


@rutas_trabajo.get("/<int:ruta_id>/planificacion/pendientes-contexto")
def planificacion_pendientes_contexto(ruta_id: int):
    """M4: pendientes territoriales — distrito_id obligatorio."""
    params = {k: (v if v != "" else None) for k, v in request.args.to_dict().items()}
    try:
        q = PlanificacionPendientesContextoQuery.model_validate(params)
        rows, total = get_planificacion_pendientes_contexto(
            ruta_id,
            distrito_id=q.distrito_id,
            tipo=q.tipo,
            prioridad=q.prioridad,
            prioridad_categoria=q.prioridad_categoria,
            q=q.q,
            turno_sugerido=q.turno_sugerido,
            calle_catalogo_id=q.calle_catalogo_id,
            page=q.page,
            per_page=q.per_page,
            orden=q.orden,
        )
        return jsonify(
            {
                "items": [iniciador_pendiente_to_row(row) for row in rows],
                "meta": {
                    "total": total,
                    "page": q.page,
                    "per_page": q.per_page,
                },
            }
        ), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
