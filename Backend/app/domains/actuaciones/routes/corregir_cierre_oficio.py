"""POST corrección de cierre por reinspección de oficio (GESTIÓN-FIX.2C)."""

from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.corregir_cierre_oficio_in import CorregirCierreOficioIn
from app.domains.actuaciones.services.corregir_cierre_oficio_service import corregir_cierre_oficio
from app.shared.errors import pydantic_errors_to_cell_map

from . import actuacion


@actuacion.post("/<int:actuacion_id>/corregir-cierre-oficio")
def corregir_cierre_oficio_route(actuacion_id: int):
    """
    Corrige resultado operativo de una actuación de circuito REINSPECCION_OFICIO.

    No reemplaza el PUT de canal actas; complementa la corrección de cumplimiento/verificar.
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    try:
        body = CorregirCierreOficioIn.model_validate(data)
        act = corregir_cierre_oficio(actuacion_id, body)
        return jsonify(actuacion_to_grid_row(act)), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
