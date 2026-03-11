from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request

from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.services.expediente_completion_service import (
    complete_expediente_from_actuacion,
)

from . import actuacion


@actuacion.post("/<int:actuacion_id>/expediente")
def crear_expediente_desde_acta(actuacion_id: int):
    """
    Crea expediente desde una actuación ramificando por `source_type` inferido en backend.

    Regla determinística:
    - Si existen notificación y comprobación, domina COMPROBACION.
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    try:
        result = complete_expediente_from_actuacion(actuacion_id, data)
        act = result["actuacion"]
        ex = result["expediente"]
        return jsonify({
            "ok": True,
            "item": actuacion_to_grid_row(act),
            "meta": {
                "actuacion_id": act.id,
                "expediente_id": ex.id,
                "expediente_numero": ex.numero_expediente,
                "fecha_expediente": ex.fecha_expediente.isoformat() if ex.fecha_expediente else None,
                "expediente_anio": ex.anio,
                "source_type": result["source_type"],
                "next_state_hint": result["next_state_hint"],
                "reinspeccion_due_date": result.get("reinspeccion_due_date"),
                "plazo_dias": result.get("plazo_dias"),
                "prorroga_dias": result.get("prorroga_dias"),
            },
        }), 201
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400

