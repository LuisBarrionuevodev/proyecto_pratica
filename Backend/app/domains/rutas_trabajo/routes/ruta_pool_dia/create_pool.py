from __future__ import annotations

from typing import Any

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.rutas_trabajo.routes.ruta_pool_dia import ruta_pool_dia
from app.domains.rutas_trabajo.schemas.ruta_pool_dia_in import RutaPoolDiaCreateIn
from app.domains.rutas_trabajo.services.auth_service import get_current_user_id_or_fallback
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import (
    create_ruta_pool_dia_entry,
    ruta_pool_dia_row_dict,
)
from app.shared.errors import pydantic_errors_to_cell_map


@ruta_pool_dia.post("")
@ruta_pool_dia.post("/")
def create_pool():
    """
    Agrega un iniciador elegible al pool del día.
    """
    data: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        payload = RutaPoolDiaCreateIn.model_validate(data)
        if payload.iniciador_ruta_id is None:
            return jsonify({"detail": "iniciador_ruta_id es obligatorio en fase 1"}), 422
        row = create_ruta_pool_dia_entry(
            fecha=payload.fecha,
            turno_id=payload.turno_id,
            usuario_id=get_current_user_id_or_fallback(),
            iniciador_ruta_id=int(payload.iniciador_ruta_id),
            origen_tipo=payload.origen_tipo,
            actuacion_id=payload.actuacion_id,
            observacion=payload.observacion,
        )
        return jsonify({"item": ruta_pool_dia_row_dict(row)}), 201
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
