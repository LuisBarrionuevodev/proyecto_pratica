"""POST preview/aplicación de vinculación de ficha a contribuyente existente."""

from __future__ import annotations

import logging

from flask import jsonify, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError

from app.database import db
from app.domains.establecimientos.schemas.vinculacion_establecimiento_in import (
    VinculacionEstablecimientoIn,
)
from app.domains.establecimientos.services.vinculacion_establecimiento_apply_service import (
    aplicar_vinculacion_establecimiento,
)
from app.domains.establecimientos.services.vinculacion_establecimiento_preview_service import (
    preview_vinculacion_establecimiento,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoError,
)
from app.domains.rutas_trabajo.services.auth_service import get_current_user_id
from app.models import User
from app.shared.errors import pydantic_errors_to_cell_map

logger = logging.getLogger(__name__)


def _actor() -> User:
    """
    Resuelve el usuario autenticado desde JWT (nunca desde el body).

    Errores:
        ValueError si no hay sesión válida.
    """
    uid = get_current_user_id()
    user = db.session.get(User, int(uid))
    if user is None or not getattr(user, "is_active", True):
        raise ValueError("Usuario no autorizado.")
    return user


def _http_error(exc: Exception):
    if isinstance(exc, ValidationError):
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(exc)}), 422
    if isinstance(exc, CorreccionEstablecimientoError):
        return jsonify(exc.to_http_body()), int(exc.status_code)
    if isinstance(exc, ValueError):
        msg = str(exc)
        status = 403 if "no autorizado" in msg.lower() else 400
        return jsonify({"detail": msg}), status
    db.session.rollback()
    logger.exception("vinculacion_establecimiento_unexpected")
    return jsonify({"detail": "Error interno del servidor."}), 500


@jwt_required()
def preview_vinculacion_establecimiento_route(establecimiento_id: int):
    """
    Vista previa del alcance de vincular la ficha a un contribuyente existente.

    No persiste. Informa destino, situación A/B y conflictos.
    """
    data = request.get_json(silent=True) or {}
    try:
        body = VinculacionEstablecimientoIn.model_validate(data)
        actor = _actor()
        payload = preview_vinculacion_establecimiento(establecimiento_id, body, actor=actor)
        return jsonify(payload), 200
    except Exception as e:
        return _http_error(e)


@jwt_required()
def aplicar_vinculacion_establecimiento_route(establecimiento_id: int):
    """
    Aplica la vinculación confirmada de forma atómica y deja auditoría.

    Requiere ``confirmado: true`` y el fingerprint del preview.
    """
    data = request.get_json(silent=True) or {}
    try:
        body = VinculacionEstablecimientoIn.model_validate(data)
        actor = _actor()
        payload = aplicar_vinculacion_establecimiento(establecimiento_id, body, actor=actor)
        return jsonify(payload), 200
    except Exception as e:
        return _http_error(e)
