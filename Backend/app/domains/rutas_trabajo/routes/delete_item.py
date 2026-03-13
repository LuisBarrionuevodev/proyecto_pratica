from __future__ import annotations

from flask import jsonify

from app.domains.rutas_trabajo.services.ruta_items_service import soft_delete_ruta_item

from . import rutas_trabajo


@rutas_trabajo.delete("/<int:ruta_id>/items/<int:item_id>")
def delete_item(ruta_id: int, item_id: int):
    """
    Soft delete de item y retorno de su iniciador a PENDIENTE.
    """
    try:
        item = soft_delete_ruta_item(ruta_id=ruta_id, item_id=item_id)
        return jsonify({"ok": True, "item_id": item.id}), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
