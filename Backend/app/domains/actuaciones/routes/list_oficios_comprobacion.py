from __future__ import annotations

from flask import jsonify

from app.domains.actuaciones.services.oficio_list_service import oficios_comprobacion_payload
from app.models import Comprobacion

from . import actuacion


@actuacion.get("/comprobaciones/<int:comprobacion_id>/oficios")
def list_oficios_comprobacion(comprobacion_id: int):
    """
    Lista oficios activos de una comprobación (preparado para PR4; no altera contratos legacy).

    Errores:
        404: comprobación inexistente.
    """
    comp = Comprobacion.query.get(comprobacion_id)
    if not comp:
        return jsonify({"detail": "Comprobación no encontrada"}), 404

    oficios = oficios_comprobacion_payload(comprobacion_id)
    return jsonify(
        {
            "comprobacion_id": comprobacion_id,
            "total": len(oficios),
            "oficios": oficios,
        }
    ), 200
