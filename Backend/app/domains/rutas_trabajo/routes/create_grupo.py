from __future__ import annotations

from typing import Any

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.rutas_trabajo.presenters.ruta_presenters import ruta_grupo_to_min_dict
from app.domains.rutas_trabajo.schemas.grupo_create_in import RutaGrupoCreateIn
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.shared.errors import pydantic_errors_to_cell_map

from . import rutas_trabajo


@rutas_trabajo.post("/<int:ruta_id>/grupos")
def create_grupo(ruta_id: int):
    """
    Crea un grupo dentro de una ruta en BORRADOR.
    """
    data: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        payload = RutaGrupoCreateIn.model_validate(data)
        grupo = create_ruta_grupo(
            ruta_id=ruta_id,
            nombre=payload.nombre,
            estado=payload.estado,
        )
        return jsonify({"item": ruta_grupo_to_min_dict(grupo)}), 201
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
