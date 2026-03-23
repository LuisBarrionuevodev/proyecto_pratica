from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.rutas_trabajo.presenters.ruta_presenters import iniciador_pendiente_to_row
from app.domains.rutas_trabajo.schemas.iniciadores_filters_in import (
    IniciadoresPendientesFiltersIn,
)
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    get_iniciadores_pendientes_para_ruta,
)
from app.shared.errors import pydantic_errors_to_cell_map

from . import rutas_trabajo


@rutas_trabajo.get("/<int:ruta_id>/iniciadores-pendientes")
def list_iniciadores_pendientes(ruta_id: int):
    """
    Lista iniciadores planificables para una ruta en BORRADOR.
    """
    params = {k: (v if v != "" else None) for k, v in request.args.to_dict().items()}
    try:
        filters = IniciadoresPendientesFiltersIn.model_validate(params)
        rows, total = get_iniciadores_pendientes_para_ruta(
            ruta_id=ruta_id,
            tipo=filters.tipo,
            prioridad=filters.prioridad,
            prioridad_categoria=filters.prioridad_categoria,
            distrito=filters.distrito,
            q=filters.q,
            turno_sugerido=filters.turno_sugerido,
            calle_catalogo_id=filters.calle_catalogo_id,
            page=filters.page,
            per_page=filters.per_page,
        )
        return jsonify(
            {
                "items": [iniciador_pendiente_to_row(row) for row in rows],
                "meta": {
                    "total": total,
                    "page": filters.page,
                    "per_page": filters.per_page,
                },
            }
        ), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
