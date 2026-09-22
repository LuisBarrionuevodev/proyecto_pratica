from __future__ import annotations

from typing import Any

from flask import jsonify, request
from pydantic import ValidationError

from app.database import db
from app.domains.orden_trabajo.schemas.secuencia_ot_schemas import OrdenTrabajoSecuenciaPatchIn
from app.domains.orden_trabajo.services.orden_trabajo_secuencia_service import (
    patch_contador_admin,
    preview_secuencia_ot,
)
from app.domains.rutas_trabajo.services.auth_service import get_current_user_id
from app.domains.usuarios.security.decorators import require_role
from app.shared.errors import pydantic_errors_to_cell_map

from . import rutas_trabajo


@rutas_trabajo.get("/secuencia-ot")
def get_secuencia_ot():
    """
    Preview read-only de la próxima OT global (sin lock ni reserva).

    Query:
        count (opcional): cantidad de OT a estimar (default 1).

    Retorno:
        next_value, next_display, estimación de rango y saltos por ocupados históricos.
    """
    raw_count = request.args.get("count", "1")
    try:
        count = int(raw_count)
    except (TypeError, ValueError):
        return jsonify({"detail": "count debe ser entero >= 0"}), 422
    if count < 0:
        return jsonify({"detail": "count debe ser >= 0"}), 422

    try:
        preview = preview_secuencia_ot(count=count)
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 503

    return jsonify(
        {
            "next_value": preview.next_value,
            "next_display": preview.next_display,
            "count": preview.count,
            "first_display": preview.first_display,
            "last_display": preview.last_display,
            "skipped_count": preview.skipped_count,
            "estimated_displays": list(preview.displays),
        }
    ), 200


@rutas_trabajo.patch("/secuencia-ot")
@require_role("admin")
def patch_secuencia_ot():
    """
    Adelanta el contador OT (solo admin, forward-only, con auditoría).

    Errores:
        401/403: auth.
        422: validación.
        409: retroceso no permitido.
    """
    data: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        payload = OrdenTrabajoSecuenciaPatchIn.model_validate(data)
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422

    actor_id = get_current_user_id()
    try:
        old_v, effective_v, effective_display, requested = patch_contador_admin(
            new_value=payload.new_value,
            reason=payload.reason,
            actor_user_id=actor_id,
        )
        db.session.commit()
    except RuntimeError as e:
        db.session.rollback()
        return jsonify({"detail": str(e)}), 409
    except ValueError as e:
        db.session.rollback()
        return jsonify({"detail": str(e)}), 422

    return jsonify(
        {
            "old_value": old_v,
            "requested_new_value": requested,
            "effective_new_value": effective_v,
            "effective_display": effective_display,
            "no_op": effective_v == old_v and requested == old_v,
        }
    ), 200
