from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, jsonify, request
from sqlalchemy import exists, and_
from sqlalchemy.orm import aliased
from app.database import db
from app.models import Actuaciones, Expediente
from app.models import Notificacion
from app.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.presenters.actuacion_presenters import actuacion_to_grid_row
from app.services.actuacion_service import (
    crear_actuacion_desde_payload,
    actualizar_actuacion_desde_payload,
    eliminar_actuacion,
)
from app.services.actuacion_helpers import acta_6


actuacion = Blueprint("actuaciones", __name__)


# =========================================================
# CREATE
# =========================================================
@actuacion.post("")
def crear_actuacion():
    """
    Recibe JSON PLANO desde la tabla del front.
    1) valida fila (Pydantic)
    2) mapea a payload estructurado
    3) crea la actuación con el service
    4) devuelve fila plana para el grid
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}

    try:
        row = ActuacionGridRowIn(**data)
        payload = map_actuacion_row(row)
        act = crear_actuacion_desde_payload(payload)

        return jsonify(actuacion_to_grid_row(act)), 201

    except ValueError as e:
        return jsonify({"detail": str(e)}), 400

    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500


# =========================================================
# UPDATE (PUT /actuaciones/<id>)
# =========================================================
@actuacion.put("/<int:actuacion_id>")
def actualizar_actuacion(actuacion_id: int):
    """
    Actualiza usando la misma lógica de grid:
    1) validación pydantic de fila
    2) mapper
    3) service update
    4) presenter plano
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}

    try:
        # metemos id al body para coherencia con mapper/service
        data["id"] = actuacion_id

        row = ActuacionGridRowIn(**data)
        payload = map_actuacion_row(row)
        act = actualizar_actuacion_desde_payload(payload)

        return jsonify(actuacion_to_grid_row(act)), 200

    except ValueError as e:
        return jsonify({"detail": str(e)}), 400

    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500


# =========================================================
# DELETE
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
# LISTAR ACTUACIONES
# =========================================================
@actuacion.get("")
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
    # existe expediente con misma comprobacion_id
    subq = exists().where(
        Expediente.comprobacion_id == Actuaciones.comprobacion_id
    )

    acts = (
        Actuaciones.query
        .filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(~subq)
        .order_by(Actuaciones.id.desc())
        .all()
    )

    return jsonify([actuacion_to_grid_row(a) for a in acts]), 200


# =========================================================
# CREAR EXPEDIENTE DESDE ACTA (POST)
#   - Esta ruta NO es PUT de actuación
#   - Es un POST puntual porque el expediente "nace" acá
#
#   POST /actuaciones/<id>/expediente
#   body:
#     { "expediente_numero": "...", "expediente_anio": 2025 }
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

    # ya existe expediente para esa comprobación
    existente = Expediente.query.filter_by(comprobacion_id=act.comprobacion_id).first()
    if existente:
        return jsonify({"detail": "Ya existe un expediente vinculado a esta comprobación"}), 409

    # unicidad por numero+anio
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

    # refrescamos act por si el presenter en el futuro usa relaciones nuevas
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
    # existe expediente para la comprobación y sin oficio
    subq = exists().where(
        (Expediente.comprobacion_id == Actuaciones.comprobacion_id)
        & (Expediente.oficio_id.is_(None))
    )

    acts = (
        Actuaciones.query
        .filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(subq)  # ✅ acá sí queremos que exista ese expediente sin oficio
        .order_by(Actuaciones.id.desc())
        .all()
    )

    return jsonify([actuacion_to_grid_row(a) for a in acts]), 200
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
        Actuaciones.query
        .filter(Actuaciones.tipo == "INSPECCION")
        .filter(Actuaciones.notificacion_id.isnot(None))
        .filter(~subq)
        .all()
    )

    return jsonify([actuacion_to_grid_row(a) for a in acts]), 200