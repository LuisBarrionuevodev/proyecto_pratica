# app/routes/actuacion.py
from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from sqlalchemy import and_, exists
from sqlalchemy.orm import aliased

from app.database import db
from app.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.models import Actuaciones, Expediente
from app.presenters.actuacion_presenters import actuacion_to_grid_row
from app.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.schemas.grid.errors import pydantic_errors_to_cell_map
from app.services.actuacion_helpers import acta_6
from app.services.actuacion_service import (
    actualizar_actuacion as actualizar_actuacion_service,
    crear_actuacion_desde_payload,
    eliminar_actuacion,
)

actuacion = Blueprint("actuaciones", __name__)


# =========================================================
# CREATE  (POST /actuaciones/)
# =========================================================
@actuacion.post("/")
def crear_actuacion():
    """
    Recibe JSON PLANO desde la tabla del front.

    Pipeline:
      1) valida fila (Pydantic)
      2) mapea a payload estructurado (mapper)
      3) crea la actuación (service)
      4) devuelve fila plana para el grid (presenter)
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}

    try:
        row = ActuacionGridRowIn.model_validate(data)
        payload = map_actuacion_row(row)

        act = crear_actuacion_desde_payload(payload)
        return jsonify(actuacion_to_grid_row(act)), 201

    except ValidationError as e:
        # errores por celda -> ideal para mostrar en grilla
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422

    except ValueError as e:
        return jsonify({"detail": str(e)}), 400

    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500


# =========================================================
# UPDATE (PUT /actuaciones/<id>)
# =========================================================
@actuacion.put("/<int:actuacion_id>")
def actualizar_actuacion_route(actuacion_id: int):
    data: Dict[str, Any] = request.get_json(silent=True) or {}

    try:
        data["id"] = actuacion_id  # ok si tu schema lo acepta

        row = ActuacionGridRowIn.model_validate(data)
        payload = map_actuacion_row(row)

        act = actualizar_actuacion_service(actuacion_id, payload)
        return jsonify(actuacion_to_grid_row(act)), 200

    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500

# =========================================================
# DELETE (DELETE /actuaciones/<id>)
# =========================================================
@actuacion.delete("/<int:actuacion_id>")
def borrar_actuacion(actuacion_id: int):
    try:
        eliminar_actuacion(actuacion_id)
        return jsonify({"detail": "Actuación eliminada"}), 200

    except ValueError as e:
        return jsonify({"detail": str(e)}), 404

    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500


# =========================================================
# LIST (GET /actuaciones/)
# =========================================================
@actuacion.get("/")
def listar_actuaciones():
    acts = Actuaciones.query.order_by(Actuaciones.id.desc()).all()
    return jsonify([actuacion_to_grid_row(a) for a in acts]), 200


# =========================================================
# PENDIENTES VINCULACIÓN ACTA
#   - Tiene acta de comprobación (comprobacion_id != None)
#   - NO tiene expediente asociado a esa comprobación
# =========================================================
@actuacion.get("/pendientes-vinc-acta")
def get_pendientes_vinc_acta():
    subq = exists().where(Expediente.comprobacion_id == Actuaciones.comprobacion_id)

    acts = (
        Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(~subq)
        .order_by(Actuaciones.id.desc())
        .all()
    )
    return jsonify([actuacion_to_grid_row(a) for a in acts]), 200


# =========================================================
# CREAR EXPEDIENTE DESDE ACTA (POST)
#   POST /actuaciones/<id>/expediente
#   body: { "expediente_numero": "...", "expediente_anio": 2025 }
# =========================================================
@actuacion.post("/<int:actuacion_id>/expediente")
def crear_expediente_desde_acta(actuacion_id: int):
    act = Actuaciones.query.get(actuacion_id)
    if not act:
        return jsonify({"detail": "Actuación no encontrada"}), 404

    if not act.comprobacion_id:
        return jsonify({"detail": "La actuación no tiene acta de comprobación"}), 400

    data: Dict[str, Any] = request.get_json(silent=True) or {}
    numero = acta_6(data.get("expediente_numero"))
    anio = data.get("expediente_anio")

    if not numero or anio is None:
        return jsonify({"detail": "expediente_numero y expediente_anio son obligatorios"}), 400

    anio_str = str(anio)

    existente = Expediente.query.filter_by(comprobacion_id=act.comprobacion_id).first()
    if existente:
        return jsonify({"detail": "Ya existe un expediente vinculado a esta comprobación"}), 409

    dup = Expediente.query.filter_by(numero_expediente=numero, anio=anio_str).first()
    if dup:
        return jsonify({"detail": "Ese expediente ya existe"}), 409

    ex = Expediente(
        numero_expediente=numero,
        anio=anio_str,
        comprobacion_id=act.comprobacion_id,
        oficio_id=None,
    )

    db.session.add(ex)
    db.session.commit()
    db.session.refresh(act)

    return jsonify(actuacion_to_grid_row(act)), 201


# =========================================================
# PENDIENTES VINCULACIÓN OFICIO
#   - Tiene acta de comprobación
#   - YA tiene expediente asociado a esa comprobación
#   - Ese expediente todavía NO tiene oficio
# =========================================================
@actuacion.get("/pendientes-vinc-oficio")
def get_pendientes_vinc_oficio():
    subq = exists().where(
        (Expediente.comprobacion_id == Actuaciones.comprobacion_id) & (Expediente.oficio_id.is_(None))
    )

    acts = (
        Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(subq)
        .order_by(Actuaciones.id.desc())
        .all()
    )
    return jsonify([actuacion_to_grid_row(a) for a in acts]), 200


# =========================================================
# PENDIENTES NOTIFICACIÓN
#   - INSPECCION con notificación cargada
#   - y todavía NO existe REINSPECCION para esa notificación
# =========================================================
@actuacion.get("/pendientes-notificacion")
def get_pendientes_notificacion():
    A2 = aliased(Actuaciones)

    subq = exists().where(
        and_(
            A2.notificacion_id == Actuaciones.notificacion_id,
            A2.tipo == "REINSPECCION",
        )
    )

    acts = (
        Actuaciones.query.filter(Actuaciones.tipo == "INSPECCION")
        .filter(Actuaciones.notificacion_id.isnot(None))
        .filter(~subq)
        .all()
    )

    return jsonify([actuacion_to_grid_row(a) for a in acts]), 200
