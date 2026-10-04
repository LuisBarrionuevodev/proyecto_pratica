from __future__ import annotations

from typing import Any

from flask import jsonify, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError

from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import RutaItemAccessError
from app.domains.media.routes import media_bp
from app.domains.media.schemas.media_schemas import UploadIntentIn
from app.domains.media.services.media_upload_intent_service import crear_upload_intent
from app.domains.rutas_trabajo.services.auth_service import get_current_user_id
from app.shared.errors import pydantic_errors_to_cell_map


@media_bp.post("/ruta-items/<int:ruta_item_id>/archivos/upload-intents")
@jwt_required()
def crear_upload_intent_route(ruta_item_id: int):
    """
    Crea registro PENDING y URL firmada PUT para subida directa al bucket privado.

    Errores:
        401/403/404: scope RutaItem.
        422: validación Pydantic o reglas de negocio.
    """
    data: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        body = UploadIntentIn.model_validate(data)
        actor_id = get_current_user_id()
        out = crear_upload_intent(
            ruta_item_id=ruta_item_id,
            body=body,
            actor_user_id=actor_id,
        )
        return jsonify(out.model_dump(mode="json")), 201
    except RutaItemAccessError as e:
        return jsonify({"detail": str(e)}), e.status_code
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 422
