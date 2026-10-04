from __future__ import annotations

from flask import jsonify
from flask_jwt_extended import jwt_required

from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import RutaItemAccessError
from app.domains.media.routes import media_bp
from app.domains.media.services.media_list_service import listar_archivos_ruta_item


@media_bp.get("/ruta-items/<int:ruta_item_id>/archivos")
@jwt_required()
def listar_archivos_ruta_item_route(ruta_item_id: int):
    """
    Lista metadata READY de archivos Media.1A del ítem (sin object_key ni URLs).

    Errores:
        401/403/404: scope RutaItem.
    """
    try:
        out = listar_archivos_ruta_item(ruta_item_id)
        return jsonify(out.model_dump(mode="json")), 200
    except RutaItemAccessError as e:
        return jsonify({"detail": str(e)}), e.status_code
