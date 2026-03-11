from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.schemas.oficio_in import OficioCreateIn
from app.domains.actuaciones.services.oficio_completion_service import complete_oficio_from_actuacion
from app.shared.errors import pydantic_errors_to_cell_map

from . import actuacion


@actuacion.post("/<int:actuacion_id>/oficio")
def crear_oficio_desde_acta(actuacion_id: int):
    """
    Crea/actualiza oficio para una actuación y crea expediente de respuesta de oficio.
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    try:
        payload = OficioCreateIn.model_validate(data)
        result = complete_oficio_from_actuacion(
            actuacion_id=actuacion_id,
            data=payload.model_dump(),
        )
        exp_original = result["expediente_original"]
        exp_resp = result["expediente_respuesta_oficio"]
        iniciador = result.get("iniciador_ruta")
        return jsonify(
            {
                "ok": True,
                "meta": {
                    "actuacion_id": actuacion_id,
                    "oficio_id": result["oficio"].id,
                    "expediente_original_id": exp_original.id,
                    "expediente_respuesta_oficio_id": exp_resp.id,
                    "iniciador_ruta_id": iniciador.id if iniciador else None,
                },
            }
        ), 201
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400

