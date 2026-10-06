from __future__ import annotations

from flask import jsonify
from flask_jwt_extended import jwt_required

from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import RutaItemAccessError
from app.domains.media.routes import media_bp
from app.domains.media.services.media_finalizar_fotos_por_ahora_service import (
    FinalizarFotosPorAhoraError,
    finalizar_fotos_pendientes_por_ahora,
)


@media_bp.post("/ruta-items/<int:ruta_item_id>/fotos/finalizar-por-ahora")
@jwt_required()
def finalizar_fotos_por_ahora_route(ruta_item_id: int):
    """
    Inspector cierra la cola de fotos pendientes sin subir más archivos (MEDIA.2C.2).

    Errores:
        401/403/404: scope RutaItem.
        422: trabajo no FINALIZADO.
    """
    try:
        out = finalizar_fotos_pendientes_por_ahora(ruta_item_id)
        return jsonify(out), 200
    except RutaItemAccessError as e:
        return jsonify({"detail": str(e)}), e.status_code
    except FinalizarFotosPorAhoraError as e:
        return jsonify({"detail": str(e)}), e.status_code
