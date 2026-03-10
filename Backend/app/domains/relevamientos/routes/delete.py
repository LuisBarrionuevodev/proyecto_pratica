from __future__ import annotations

from flask import jsonify

from app.domains.relevamientos.services.delete_service import eliminar_relevamiento
from app.domains.relevamientos.services.operational_guard_service import RelevamientoNoOperativoError

from . import relevamiento


@relevamiento.delete("/<int:relevamiento_id>")
def borrar_relevamiento(relevamiento_id: int):
    """
    Elimina un relevamiento por id.
    """
    try:
        eliminar_relevamiento(relevamiento_id)
        return jsonify({"ok": True}), 200
    except RelevamientoNoOperativoError as e:
        return jsonify({"detail": str(e)}), 409
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
