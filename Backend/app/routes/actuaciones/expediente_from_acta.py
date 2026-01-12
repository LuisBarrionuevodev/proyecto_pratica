from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request

from app.database import db
from app.models import Actuaciones, Expediente
from app.presenters.actuacion_presenters import actuacion_to_grid_row
from app.utils.actas import acta_6

from . import actuacion


@actuacion.post("/<int:actuacion_id>/expediente")
def crear_expediente_desde_acta(actuacion_id: int):
    """Crea un expediente a partir de una actuación con comprobación."""
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

