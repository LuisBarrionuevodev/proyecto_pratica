from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.utils.actuaciones_bandeja_eager import (
    reload_actuaciones_inspeccion_checklist_eager,
)
from app.domains.actuaciones.presenters.actuacion_gestion_seguimiento_presenter import (
    present_actuacion_gestion_detalle,
)
from app.domains.usuarios.security.inspector_scope_policy import InspectorScopeError
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.schemas.actuacion_patch_in import ActuacionPatchIn
from app.shared.errors import pydantic_errors_to_cell_map
from app.domains.actuaciones.utils.circuito_operativo import (
    build_actuacion_grid_validation_context,
)
from app.domains.actuaciones.services.actuaciones_actuacion_inspector_scope import (
    assert_inspector_puede_acceder_actuacion,
)
from app.domains.actuaciones.services.actuacion_inspector_put_policy import (
    assert_inspector_raw_json_solo_campos_permitidos,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion as actualizar_actuacion_service
from app.domains.rutas_trabajo.services.auth_service import get_current_user_id
from app.domains.usuarios.security.decorators import resolve_user_from_identity
from app.domains.usuarios.services.inspector_link_service import INSPECTOR_ROLE
from app.domains.actuaciones.services.actuacion_corregir_cierre_operativo_service import (
    CorregirCierreOperativoError,
)
from app.domains.actuaciones.services.patch_service import actualizar_actuacion_parcial
from app.domains.actuaciones.utils.put_actuacion_diag import (
    log_exception,
    log_put_request,
)

from . import actuacion


@actuacion.put("/<int:actuacion_id>")
def actualizar_actuacion_route(actuacion_id: int):
    """Actualiza por **CargarActuacion** (PUT con fila completa); no es flujo de oficio/expediente."""
    try:
        raw_json = request.get_json(silent=True)
        if raw_json is not None and not isinstance(raw_json, dict):
            return (
                jsonify({"detail": "Validation error", "errors": {"_global": "JSON inválido"}}),
                422,
            )
        data: Dict[str, Any] = dict(raw_json) if isinstance(raw_json, dict) else {}

        user = resolve_user_from_identity()
        if user is not None and user.role == INSPECTOR_ROLE:
            assert_inspector_puede_acceder_actuacion(int(actuacion_id))
            assert_inspector_raw_json_solo_campos_permitidos(data)

        data["id"] = actuacion_id

        validation_ctx = build_actuacion_grid_validation_context(actuacion_id)
        row = ActuacionGridRowIn.model_validate(
            data,
            context=validation_ctx,
        )
        payload = map_actuacion_row(row)
        log_put_request(actuacion_id, data, payload)

        actor_user_id = get_current_user_id()
        act = actualizar_actuacion_service(
            actuacion_id, payload, actor_user_id=actor_user_id
        )
        act_reload = reload_actuaciones_inspeccion_checklist_eager([act])[0]
        return jsonify(present_actuacion_gestion_detalle(act_reload)), 200

    except InspectorScopeError as e:
        return jsonify({"detail": str(e)}), e.status_code
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except CorregirCierreOperativoError as e:
        return jsonify({"detail": str(e)}), 409
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        log_exception(actuacion_id, e)
        return jsonify({"detail": "Error interno", "error": str(e)}), 500


@actuacion.patch("/<int:actuacion_id>")
def actualizar_actuacion_parcial_route(actuacion_id: int):
    return jsonify({"detail": "PATCH deshabilitado. Usar PUT con payload completo."}), 405
