from __future__ import annotations

from flask import jsonify
from sqlalchemy import exists

from app.models import Actuaciones, Expediente
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row

from . import actuacion


@actuacion.get("/pendientes-vinc-acta")
def get_pendientes_vinc_acta():
    """Lista actuaciones pendientes de vinculación de acta (expediente)."""
    subq = exists().where(Expediente.comprobacion_id == Actuaciones.comprobacion_id)

    acts = (
        Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(~subq)
        .order_by(Actuaciones.id.desc())
        .all()
    )
    return jsonify([actuacion_to_grid_row(a) for a in acts]), 200

