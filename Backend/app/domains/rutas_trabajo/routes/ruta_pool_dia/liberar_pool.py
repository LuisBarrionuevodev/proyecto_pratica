from __future__ import annotations

from flask import jsonify

from app.domains.rutas_trabajo.routes.ruta_pool_dia import ruta_pool_dia
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import (
    liberar_ruta_pool_dia_entry,
    ruta_pool_dia_row_dict,
)


@ruta_pool_dia.post("/<int:pool_id>/liberar")
def liberar_pool(pool_id: int):
    """
    Libera pendiente del pool o ruta borrador (transaccional).

    - ``EN_POOL`` sin ítem: descarta pool.
    - ``ASIGNADO_A_RUTA`` en BORRADOR sin OT: elimina ítem y descarta pool.
    """
    try:
        row = liberar_ruta_pool_dia_entry(pool_id=pool_id)
        return jsonify({"item": ruta_pool_dia_row_dict(row)}), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
