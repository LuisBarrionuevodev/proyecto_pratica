"""
Obtener una ficha ``establecimiento_operativo`` por id con relaciones y agregados de actuaciones.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.establecimientos.utils.domicilio_display import domicilio_texto_ficha_detalle
from app.models import Actuaciones, Domicilio, EstablecimientoOperativo


def get_establecimiento_operativo_con_metricas(
    establecimiento_id: int,
) -> tuple[EstablecimientoOperativo | None, int, date | None, Domicilio | None]:
    """
    Carga una ficha por id con domicilio/contrib/rubro/distrito y calcula métricas de actuaciones.

    Parámetros:
        establecimiento_id: PK de ``establecimiento_operativo``.

    Retorno:
        Tupla ``(eo | None, actuaciones_count, ultima_fecha | None, domicilio_ultima_actuacion | None)``.
        Si no existe la ficha, ``(None, 0, None, None)``.
    """
    eo = (
        EstablecimientoOperativo.query.filter(EstablecimientoOperativo.id == establecimiento_id)
        .options(
            joinedload(EstablecimientoOperativo.domicilio).joinedload(Domicilio.contribuyente),
            joinedload(EstablecimientoOperativo.domicilio).joinedload(Domicilio.rubro),
            joinedload(EstablecimientoOperativo.domicilio).joinedload(Domicilio.distrito),
            joinedload(EstablecimientoOperativo.domicilio).joinedload(Domicilio.calle_catalogo),
        )
        .first()
    )
    if eo is None:
        return None, 0, None, None

    dom = eo.domicilio
    if dom is not None and dom.deleted_at is not None:
        return None, 0, None, None

    cnt = (
        db.session.query(func.count(Actuaciones.id))
        .filter(Actuaciones.establecimiento_operativo_id == establecimiento_id)
        .scalar()
    )
    cnt_int = int(cnt or 0)

    ultima = (
        db.session.query(func.max(Actuaciones.fecha))
        .filter(Actuaciones.establecimiento_operativo_id == establecimiento_id)
        .scalar()
    )

    ultima_act = (
        Actuaciones.query.filter(Actuaciones.establecimiento_operativo_id == establecimiento_id)
        .options(joinedload(Actuaciones.domicilio).joinedload(Domicilio.calle_catalogo))
        .order_by(Actuaciones.fecha.desc(), Actuaciones.id.desc())
        .first()
    )
    dom_ultima_act = ultima_act.domicilio if ultima_act is not None else None

    return eo, cnt_int, ultima, dom_ultima_act
