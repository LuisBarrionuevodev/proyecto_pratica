"""
Historial de actuaciones por ficha ``establecimiento_operativo``.
"""

from __future__ import annotations

from sqlalchemy.orm import joinedload

from app.models import Actuaciones, EstablecimientoOperativo


def list_actuaciones_por_establecimiento_operativo(
    establecimiento_id: int,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Actuaciones], int]:
    """
    Actuaciones con ``establecimiento_operativo_id`` ordenadas por fecha descendente.

    Parámetros:
        establecimiento_id: FK a la ficha.
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

    base = Actuaciones.query.filter(Actuaciones.establecimiento_operativo_id == establecimiento_id)
    total = base.count()

    q = base.options(
        joinedload(Actuaciones.orden_trabajo),
        joinedload(Actuaciones.inspeccion),
    ).order_by(Actuaciones.fecha.desc(), Actuaciones.id.desc())

    offset = (page - 1) * page_size
    items = q.offset(offset).limit(page_size).all()
    return items, total
