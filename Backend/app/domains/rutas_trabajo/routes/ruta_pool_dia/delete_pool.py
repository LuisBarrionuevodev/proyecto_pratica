from __future__ import annotations

from flask import jsonify

from app.domains.rutas_trabajo.routes.ruta_pool_dia import ruta_pool_dia
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import (
    descartar_ruta_pool_dia_entry,
    ruta_pool_dia_row_dict,
)


@ruta_pool_dia.delete("/<int:pool_id>")
def delete_pool(pool_id: int):
    """
    Baja lógica de entrada del pool (estado DESCARTADO).
    """
    try:
        row = descartar_ruta_pool_dia_entry(pool_id=pool_id)
        return jsonify({"item": ruta_pool_dia_row_dict(row)}), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
