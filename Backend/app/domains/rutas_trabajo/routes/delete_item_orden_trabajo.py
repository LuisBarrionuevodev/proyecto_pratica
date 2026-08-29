from __future__ import annotations

from flask import jsonify

from app.domains.rutas_trabajo.presenters.ruta_presenters import ruta_item_to_min_dict
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    liberar_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.utils.ruta_publicar_debug import json_409_publicar

from . import rutas_trabajo


@rutas_trabajo.delete("/<int:ruta_id>/items/<int:item_id>/orden-trabajo")
def delete_item_orden_trabajo(ruta_id: int, item_id: int):
    """
    Libera la OT del ítem (``orden_trabajo_id = NULL``). No elimina la entidad OrdenTrabajo.
    """
    try:
        item = liberar_orden_trabajo_on_item(ruta_id=ruta_id, item_id=item_id)
        return jsonify({"item": ruta_item_to_min_dict(item)}), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        body, status = json_409_publicar(e)
        return jsonify(body), status
