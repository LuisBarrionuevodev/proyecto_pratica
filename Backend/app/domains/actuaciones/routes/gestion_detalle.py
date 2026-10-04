from __future__ import annotations

from flask import jsonify
from flask_jwt_extended import jwt_required

from app.domains.actuaciones.services.actuacion_gestion_detalle_service import (
    obtener_actuacion_gestion_detalle,
)
from app.domains.usuarios.security.inspector_scope_policy import InspectorScopeError

from . import actuacion


@actuacion.get("/<int:actuacion_id>/gestion")
@jwt_required()
def get_actuacion_gestion_detalle_route(actuacion_id: int):
    """
    Detalle autorizado de una actuación para el modal de Gestión (seguimiento + teléfono en ``seguimiento``).

    Errores:
        403: scope de inspector.
        404: actuación inexistente.
    """
    try:
        payload = obtener_actuacion_gestion_detalle(actuacion_id)
        return jsonify(payload), 200
    except InspectorScopeError as e:
        return jsonify({"detail": str(e)}), e.status_code
    except ValueError as e:
        return jsonify({"detail": str(e)}), 404
