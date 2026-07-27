from __future__ import annotations

from typing import Any

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.rutas_trabajo.presenters.ruta_presenters import ruta_item_to_min_dict
from app.domains.rutas_trabajo.schemas.item_orden_trabajo_patch_in import (
    RutaItemOrdenTrabajoPatchIn,
)
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.utils.ruta_publicar_debug import json_409_publicar
from app.shared.errors import pydantic_errors_to_cell_map

from . import rutas_trabajo


@rutas_trabajo.patch("/<int:ruta_id>/items/<int:item_id>/orden-trabajo")
def patch_item_orden_trabajo(ruta_id: int, item_id: int):
    """
    Asigna/reemplaza OT en un item de ruta en BORRADOR.
    """
    data: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        payload = RutaItemOrdenTrabajoPatchIn.model_validate(data)
        item = set_orden_trabajo_on_item(
            ruta_id=ruta_id,
            item_id=item_id,
            numero_orden_trabajo=payload.numero_orden_trabajo,
        )
        return jsonify({"item": ruta_item_to_min_dict(item)}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        body, status = json_409_publicar(e)
        return jsonify(body), status
