from __future__ import annotations

from flask import jsonify
from flask_jwt_extended import jwt_required

from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import RutaItemAccessError
from app.domains.media.routes import media_bp
from app.domains.media.services.media_access_service import MediaAccessError
from app.domains.media.services.media_download_service import obtener_download_url


@media_bp.get("/archivos/<int:archivo_id>/download-url")
@jwt_required()
def download_url_route(archivo_id: int):
    """
    Devuelve URL firmada GET temporal para un archivo READY.

    Errores:
        422: estado no descargable.
        401/403/404: autorización.
    """
    try:
        out = obtener_download_url(archivo_id)
        return jsonify(out.model_dump(mode="json")), 200
    except RutaItemAccessError as e:
        return jsonify({"detail": str(e)}), e.status_code
    except MediaAccessError as e:
        return jsonify({"detail": str(e)}), e.status_code
    except ValueError as e:
        return jsonify({"detail": str(e)}), 422
