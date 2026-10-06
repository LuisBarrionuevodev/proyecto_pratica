from __future__ import annotations

from flask import jsonify
from flask_jwt_extended import jwt_required

from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import RutaItemAccessError
from app.domains.media.routes import media_bp
from app.domains.media.services.media_access_service import MediaAccessError
from app.domains.media.errors import MediaDomainError, media_error_json
from app.domains.media.services.media_complete_service import completar_carga_archivo


@media_bp.post("/archivos/<int:archivo_id>/complete")
@jwt_required()
def completar_archivo_route(archivo_id: int):
    """
    Confirma carga tras validar objeto en storage (HEAD, MIME, magic bytes, SHA-256).

    Errores:
        422: validación del objeto.
        401/403/404: autorización.
    """
    try:
        out = completar_carga_archivo(archivo_id)
        return jsonify(out.model_dump(mode="json")), 200
    except RutaItemAccessError as e:
        return jsonify({"detail": str(e)}), e.status_code
    except MediaAccessError as e:
        return jsonify({"detail": str(e)}), e.status_code
    except MediaDomainError as e:
        return jsonify(media_error_json(e)), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 422
