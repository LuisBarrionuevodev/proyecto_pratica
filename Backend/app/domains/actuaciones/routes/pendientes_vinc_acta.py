from __future__ import annotations

from flask import jsonify
from sqlalchemy import and_, exists

from app.models import Actuaciones, Expediente
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row

from . import actuacion


@actuacion.get("/pendientes-vinc-acta")
def get_pendientes_vinc_acta():
    """
    Actuaciones con comprobación que aún no tienen **expediente de envío** (`oficio_id` NULL).

    No cuenta el expediente de respuesta de oficio como “ya vinculado”.
    """
    subq = exists().where(
        and_(
            Expediente.comprobacion_id == Actuaciones.comprobacion_id,
            Expediente.oficio_id.is_(None),
        )
    )

    acts = (
        Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(~subq)
        .order_by(Actuaciones.id.desc())
        .all()
    )
    counts_by_eo = build_counts_by_eo_from_actuaciones(acts)
    return jsonify([actuacion_to_grid_row(a, counts_by_eo=counts_by_eo) for a in acts]), 200

