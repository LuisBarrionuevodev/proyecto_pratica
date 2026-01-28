from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import func

from app.models import Relevamiento, Inspector, Domicilio
from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters


def listar_relevamientos_con_filtros(filters: RelevamientosListFilters) -> Dict[str, Any]:
    """
    Lista relevamientos aplicando filtros y paginación.

    Args:
        filters: filtros validados (desde, hasta, inspector, calle, numero).

    Returns:
        dict con items y meta.
    """
    query = Relevamiento.query

    if filters.desde:
        query = query.filter(Relevamiento.fecha >= filters.desde)
    if filters.hasta:
        query = query.filter(Relevamiento.fecha <= filters.hasta)

    if filters.inspector:
        s = str(filters.inspector).strip()
        if s.isdigit():
            query = query.filter(Relevamiento.inspector_id == int(s))
        else:
            query = query.join(Inspector).filter(func.upper(Inspector.nombre) == s.upper())

    if filters.calle or filters.numero:
        query = query.join(Domicilio, Relevamiento.domicilio_id == Domicilio.id)
        if filters.calle:
            query = query.filter(func.upper(Domicilio.calle).like(f"%{filters.calle.upper()}%"))
        if filters.numero:
            query = query.filter(Domicilio.numero == str(filters.numero).strip())

    total = query.count()
    query = query.order_by(Relevamiento.id.desc())
    offset = (filters.page - 1) * filters.page_size
    items = query.offset(offset).limit(filters.page_size).all()

    return {
        "items": items,
        "meta": {
            "total": total,
            "page": filters.page,
            "page_size": filters.page_size,
            "desde": filters.desde.isoformat() if filters.desde else None,
            "hasta": filters.hasta.isoformat() if filters.hasta else None,
            "inspector": filters.inspector,
            "calle": filters.calle,
            "numero": filters.numero,
        },
    }
