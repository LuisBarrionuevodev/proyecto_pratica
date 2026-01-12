from __future__ import annotations

from flask import jsonify
from sqlalchemy import and_, exists
from sqlalchemy.orm import aliased

from app.models import Actuaciones
from app.presenters.actuacion_presenters import actuacion_to_grid_row

from . import actuacion


@actuacion.get("/pendientes-notificacion")
def get_pendientes_notificacion():
    """Lista inspecciones con notificación sin reinspección."""
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

