from __future__ import annotations

from flask import jsonify

from app.domains.rutas_trabajo.presenters.ruta_presenters import (
    ruta_grupo_to_min_dict,
    ruta_trabajo_to_dict,
)
from app.domains.rutas_trabajo.services.ruta_detail_service import get_ruta_detail_min

from . import rutas_trabajo


@rutas_trabajo.get("/<int:ruta_id>")
def detail_ruta(ruta_id: int):
    """
    Retorna detalle mínimo de ruta para PR2.
    """
    try:
        ruta, grupos = get_ruta_detail_min(ruta_id)
        return jsonify(
            {
                "ruta": ruta_trabajo_to_dict(ruta),
                "grupos": [ruta_grupo_to_min_dict(g) for g in grupos],
            }
        ), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
