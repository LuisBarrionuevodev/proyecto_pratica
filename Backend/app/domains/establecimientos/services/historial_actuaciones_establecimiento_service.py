"""
Historial de actuaciones por ficha ``establecimiento_operativo``.
"""

from __future__ import annotations

from sqlalchemy.orm import joinedload

from app.domains.actuaciones.utils.actuaciones_bandeja_eager import apply_bandeja_grid_eager
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    actuaciones_filter_identidad_logica_desde_domicilio,
    count_actuaciones_identidad_logica,
)
from app.models import Actuaciones, Domicilio, EstablecimientoOperativo


def _actuaciones_historial_filter(establecimiento_id: int, domicilio_id: int | None):
    """
    Filtro de historial por identidad lógica (contribuyente + domicilio normalizado).

    Incluye actuaciones en forks COW del mismo local aunque tengan EO distinto o NULL.
    """
    from sqlalchemy import or_

    eo = EstablecimientoOperativo.query.filter_by(id=establecimiento_id).first()
    if eo is None or eo.domicilio is None:
        clauses = [Actuaciones.establecimiento_operativo_id == establecimiento_id]
        if domicilio_id is not None:
            clauses.append(Actuaciones.domicilio_id == domicilio_id)
        return or_(*clauses)

    dom = eo.domicilio
    return actuaciones_filter_identidad_logica_desde_domicilio(dom)


def list_actuaciones_por_establecimiento_operativo(
    establecimiento_id: int,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Actuaciones], int]:
    """
    Actuaciones de la identidad lógica de la ficha, ordenadas por fecha descendente.

    Parámetros:
        establecimiento_id: FK a la ficha (canónica o duplicada histórica).
        page: página 1-based.
        page_size: tamaño de página.

    Retorno:
        Tupla (items, total).

    Errores:
        Ninguno; si la ficha no existe el total será 0 (el caller puede devolver 404 antes).
    """
    exists = EstablecimientoOperativo.query.filter_by(id=establecimiento_id).first()
    if exists is None:
        return [], 0

    domicilio_id = exists.domicilio_id
    base = Actuaciones.query.filter(_actuaciones_historial_filter(establecimiento_id, domicilio_id))
    total = base.count()

    q = (
        apply_bandeja_grid_eager(base)
        .options(joinedload(Actuaciones.domicilio).joinedload(Domicilio.calle_catalogo))
        .order_by(Actuaciones.fecha.desc(), Actuaciones.id.desc())
    )

    offset = (page - 1) * page_size
    items = q.offset(offset).limit(page_size).all()
    return items, total


def total_actuaciones_identidad_logica_establecimiento(establecimiento_id: int) -> int:
    """Total de actuaciones de la identidad lógica asociada a la ficha."""
    eo = EstablecimientoOperativo.query.filter_by(id=establecimiento_id).first()
    if eo is None or eo.domicilio is None:
        return 0
    return count_actuaciones_identidad_logica(eo.domicilio)
