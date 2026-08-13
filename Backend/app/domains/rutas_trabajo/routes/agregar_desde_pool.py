from __future__ import annotations

from typing import Any

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.rutas_trabajo.presenters.ruta_presenters import ruta_item_to_min_dict
from app.domains.rutas_trabajo.schemas.ruta_pool_dia_in import RutaPoolAgregarDesdePoolIn
from app.domains.rutas_trabajo.services.ruta_pool_agregar_desde_pool_service import (
    agregar_desde_pool_a_ruta,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import ruta_pool_dia_row_dict
from app.shared.errors import pydantic_errors_to_cell_map

from . import rutas_trabajo


@rutas_trabajo.post("/<int:ruta_id>/agregar-desde-pool")
def agregar_desde_pool(ruta_id: int):
    """
    Asigna filas EN_POOL a un grupo de ruta BORRADOR.

    Body: ``pool_ids`` (lista), ``grupo_id`` (obligatorio).
    """
    data: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        payload = RutaPoolAgregarDesdePoolIn.model_validate(data)
        result = agregar_desde_pool_a_ruta(
            ruta_id=ruta_id,
            grupo_id=payload.grupo_id,
            pool_ids=payload.pool_ids,
        )
        return jsonify(
            {
                "items": [ruta_item_to_min_dict(i) for i in result["items"]],
                "pool_rows": [ruta_pool_dia_row_dict(r) for r in result["pool_rows"]],
            }
        ), 201
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
