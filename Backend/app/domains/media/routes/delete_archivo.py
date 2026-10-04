from __future__ import annotations

from flask import jsonify
from flask_jwt_extended import jwt_required

from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import RutaItemAccessError
from app.domains.media.routes import media_bp
from app.domains.media.services.media_access_service import MediaAccessError
from app.domains.media.services.media_delete_service import eliminar_archivo
from app.domains.rutas_trabajo.services.auth_service import get_current_user_id


@media_bp.delete("/archivos/<int:archivo_id>")
@jwt_required()
def eliminar_archivo_route(archivo_id: int):
    """
    Elimina archivo READY de Media.1A (bucket + soft delete).

    Errores:
        400/422: reglas de negocio o fallo de storage.
        401/403/404: autorización.
    """
    try:
        actor_id = get_current_user_id()
        out = eliminar_archivo(archivo_id, actor_user_id=actor_id)
        return jsonify(out.model_dump(mode="json")), 200
    except RutaItemAccessError as e:
        return jsonify({"detail": str(e)}), e.status_code
    except MediaAccessError as e:
        return jsonify({"detail": str(e)}), e.status_code
    except ValueError as e:
        return jsonify({"detail": str(e)}), 422
