from __future__ import annotations

from flask import Blueprint, request, jsonify
from app.models import Actuaciones
from app.schemas.grid.actuacion_row import ActuacionGridRowIn
from app.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.services.actuacion_service import crear_actuacion_desde_payload
from app.services.actuacion_service import actualizar_actuacion_desde_payload
from app.services.actuacion_service import eliminar_actuacion
from app.presenters.actuacion_presenters import actuacion_to_grid_row

actuacion = Blueprint("actuaciones", __name__)


@actuacion.post("")
def crear_actuacion():
    """
    Recibe JSON PLANO desde la tabla del front.
    1) valida fila (Pydantic)
    2) mapea a payload estructurado
    3) crea la actuación con el service
    """

    data = request.get_json(silent=True) or {}

    try:
        # 1) validación de fila
        row = ActuacionGridRowIn(**data)

        # 2) mapping limpio
        payload = map_actuacion_row(row)

        # 3) creación real
        actuacion = crear_actuacion_desde_payload(payload)

        # respuesta simple (ajustá según tu to_dict real)
        return jsonify(actuacion_to_grid_row(actuacion)), 201


    except ValueError as e:
        return jsonify({"detail": str(e)}), 400

    except Exception as e:
        # error inesperado
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
    


@actuacion.put("/<int:actuacion_id>")
def actualizar_actuacion(actuacion_id: int):
    data = request.get_json(silent=True) or {}

    try:
        # opcional: meter el id al body para que el mapper/service lo use
        data["id"] = actuacion_id

        row = ActuacionGridRowIn(**data)
        payload = map_actuacion_row(row)

        actuacion = actualizar_actuacion_desde_payload(payload)

        return jsonify(actuacion_to_grid_row(actuacion)), 200

    except ValueError as e:
        return jsonify({"detail": str(e)}), 400

    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500




@actuacion.delete("/<int:actuacion_id>")
def borrar_actuacion(actuacion_id: int):
    try:
        eliminar_actuacion(actuacion_id)
        return jsonify({"detail": "Actuación eliminada"}), 200

    except ValueError as e:
        return jsonify({"detail": str(e)}), 404

    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500    
    
@actuacion.get("")
def listar_actuaciones():
    acts = Actuaciones.query.order_by(Actuaciones.id.desc()).all()
    return jsonify([actuacion_to_grid_row(a) for a in acts]), 200    