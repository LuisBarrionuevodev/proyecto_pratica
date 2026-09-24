from __future__ import annotations

from typing import Any

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.rutas_trabajo.presenters.ruta_presenters import ruta_item_to_min_dict
from app.domains.rutas_trabajo.schemas.move_item_in import RutaItemMoveIn
from app.domains.rutas_trabajo.services.ruta_items_service import move_ruta_item
from app.shared.errors import pydantic_errors_to_cell_map

from . import rutas_trabajo


@rutas_trabajo.patch("/<int:ruta_id>/items/<int:item_id>/move")
def move_item(ruta_id: int, item_id: int):
    """
    Mueve un item activo entre grupos de una ruta en BORRADOR.
    """
    data: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        payload = RutaItemMoveIn.model_validate(data)
        item = move_ruta_item(
            ruta_id=ruta_id,
            item_id=item_id,
            target_grupo_id=payload.target_grupo_id,
        )
        return jsonify({"item": ruta_item_to_min_dict(item)}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
