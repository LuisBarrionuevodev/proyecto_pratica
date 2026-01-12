from __future__ import annotations

from flask import jsonify

from app.services.actuaciones.delete_service import eliminar_actuacion

from . import actuacion


@actuacion.delete("/<int:actuacion_id>")
def borrar_actuacion(actuacion_id: int):
    """Elimina una actuación."""
    try:
        eliminar_actuacion(actuacion_id)
        return jsonify({"detail": "Actuación eliminada"}), 200

    except ValueError as e:
        return jsonify({"detail": str(e)}), 404

    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500

