from __future__ import annotations

from flask import jsonify

from app.models import Actuaciones
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row

from . import actuacion


@actuacion.get("/")
def listar_actuaciones():
    """Lista actuaciones (orden desc por id)."""
    acts = Actuaciones.query.order_by(Actuaciones.id.desc()).all()
    return jsonify([actuacion_to_grid_row(a) for a in acts]), 200

