from __future__ import annotations

from flask import jsonify

from app.domains.rutas_trabajo.services.ruta_items_service import soft_delete_grupo

from . import rutas_trabajo


@rutas_trabajo.delete("/<int:ruta_id>/grupos/<int:grupo_id>")
def delete_grupo(ruta_id: int, grupo_id: int):
    """
    Soft delete de grupo y de items activos, devolviendo iniciadores a PENDIENTE.
    """
    try:
        result = soft_delete_grupo(ruta_id=ruta_id, grupo_id=grupo_id)
        return jsonify({"ok": True, **result}), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
