from __future__ import annotations

from typing import Any

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.rutas_trabajo.presenters.ruta_presenters import ruta_item_to_min_dict
from app.domains.rutas_trabajo.schemas.assign_items_in import RutaItemsAssignIn
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.shared.errors import pydantic_errors_to_cell_map

from . import rutas_trabajo


@rutas_trabajo.post("/<int:ruta_id>/grupos/<int:grupo_id>/items:assign")
def assign_items(ruta_id: int, grupo_id: int):
    """
    Asignación bulk de iniciadores a grupo.
    """
    data: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        payload = RutaItemsAssignIn.model_validate(data)
        items = assign_iniciadores_to_grupo(
            ruta_id=ruta_id,
            grupo_id=grupo_id,
            iniciador_ids=payload.iniciador_ids,
        )
        return jsonify({"items": [ruta_item_to_min_dict(i) for i in items]}), 201
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
