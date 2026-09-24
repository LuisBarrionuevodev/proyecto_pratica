"""
POST autenticado: importar entry EpiCollect sobre una actuación (matching por id).
"""

from __future__ import annotations

from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError

from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row

from app.domains.actuaciones.schemas.epicollect_import_from_api_in import EpicollectImportFromApiIn
from app.domains.actuaciones.schemas.epicollect_import_in import EpicollectImportIn
from app.domains.actuaciones.services.epicollect_import_service import (
    EpicollectImportConflictError,
    import_epicollect_entry,
)
from app.domains.actuaciones.services.epicollect_remote_import_service import (
    fetch_and_import_epicollect_entry,
)
from app.integrations.epicollect.errors import (
    EpicollectAuthError,
    EpicollectClientError,
    EpicollectConfigError,
    EpicollectEntryNotFoundError,
    EpicollectHttpError,
    EpicollectNetworkError,
)

from app.security.rate_limiter import limit_epicollect_import, limiter

from . import actuacion


@actuacion.post("/<int:actuacion_id>/epicollect/import")
@limiter.limit(limit_epicollect_import)
@jwt_required()
def epicollect_import(actuacion_id: int):
    """
    Importa un entry EpiCollect5 sobre la actuación indicada.

    - Setea `ec5_uuid` con el UUID del entry (validación fuerte de conflictos).
    - Sincroniza `actuacion_media` para campos en allowlist (`epicollect.<field_id>`).
    - Upsert en `actuacion_epicollect_detalle` con respuestas no-media (`payload_non_media`).

    Body JSON:
        { "payload": { ... } }

    Returns:
        200: { "actuacion": <grid row>, "media_count": N }
        400: validación / negocio
        401: sin JWT
        404: actuación inexistente
        409: conflicto ec5_uuid
    """
    raw = request.get_json(silent=True)
    if not isinstance(raw, dict):
        return jsonify({"detail": "Body JSON inválido."}), 400

    try:
        body = EpicollectImportIn.model_validate(raw)
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": e.errors()}), 422

    try:
        act, media_count = import_epicollect_entry(actuacion_id, body.payload)
    except EpicollectImportConflictError as e:
        return jsonify({"detail": str(e)}), 409
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            return jsonify({"detail": msg}), 404
        return jsonify({"detail": msg}), 400

    return (
        jsonify(
            {
                "actuacion": actuacion_to_grid_row(act),
                "media_count": media_count,
            }
        ),
        200,
    )


@actuacion.post("/<int:actuacion_id>/epicollect/import-from-api")
@limiter.limit(limit_epicollect_import)
@jwt_required()
def epicollect_import_from_api(actuacion_id: int):
    """
    Descarga un entry desde la API de exportación EpiCollect5 e importa sobre la actuación.

    Body JSON:
        { "ec5_uuid": "<uuid del entry>" }

    Configuración (env / app.config): EPICOLLECT_PROJECT_SLUG, EPICOLLECT_BASE_URL,
    EPICOLLECT_FORM_REF (opcional), EPICOLLECT_CLIENT_ID / SECRET (proyecto privado).

    Returns:
        200: mismo shape que ``/epicollect/import``
        400: ec5_uuid inválido
        401: sin JWT
        404: actuación o entry remoto inexistente
        409: conflicto ec5_uuid (import interno)
        502/503/504: fallos de EpiCollect (auth, HTTP, red, config)
    """
    raw = request.get_json(silent=True)
    if not isinstance(raw, dict):
        return jsonify({"detail": "Body JSON inválido."}), 400

    try:
        body = EpicollectImportFromApiIn.model_validate(raw)
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": e.errors()}), 422

    try:
        act, media_count = fetch_and_import_epicollect_entry(
            actuacion_id,
            body.ec5_uuid,
            app_config=dict(current_app.config),
        )
    except EpicollectConfigError as e:
        return jsonify({"detail": str(e)}), 503
    except EpicollectEntryNotFoundError as e:
        return jsonify({"detail": str(e)}), 404
    except EpicollectAuthError as e:
        return jsonify({"detail": str(e)}), 502
    except EpicollectHttpError as e:
        return jsonify({"detail": str(e), "status_code": e.status_code}), 502
    except EpicollectNetworkError as e:
        return jsonify({"detail": str(e)}), 504
    except EpicollectImportConflictError as e:
        return jsonify({"detail": str(e)}), 409
    except EpicollectClientError as e:
        return jsonify({"detail": str(e)}), 502
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            return jsonify({"detail": msg}), 404
        return jsonify({"detail": msg}), 400

    return (
        jsonify(
            {
                "actuacion": actuacion_to_grid_row(act),
                "media_count": media_count,
            }
        ),
        200,
    )
