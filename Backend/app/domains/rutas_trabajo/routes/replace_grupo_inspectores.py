from __future__ import annotations

from typing import Any

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.rutas_trabajo.presenters.ruta_presenters import grupo_inspector_to_dict
from app.domains.rutas_trabajo.schemas.grupo_inspectores_replace_in import (
    RutaGrupoInspectoresReplaceIn,
)
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.shared.errors import pydantic_errors_to_cell_map

from . import rutas_trabajo


@rutas_trabajo.put("/<int:ruta_id>/grupos/<int:grupo_id>/inspectores")
def replace_inspectores(ruta_id: int, grupo_id: int):
    """
    Reemplaza totalmente inspectores asignados a un grupo.
    """
    data: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        payload = RutaGrupoInspectoresReplaceIn.model_validate(data)
        rows = replace_grupo_inspectores(
            ruta_id=ruta_id,
            grupo_id=grupo_id,
            inspector_ids=payload.inspector_ids,
        )
        return jsonify({"items": [grupo_inspector_to_dict(r) for r in rows]}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
