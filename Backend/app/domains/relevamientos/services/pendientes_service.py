from __future__ import annotations

from typing import Dict, List

from sqlalchemy import or_

from app.models import Relevamiento, Domicilio
from app.domains.relevamientos.schemas.pendientes_filters import RelevamientosPendientesFilters


def _apply_fecha(query, desde, hasta):
    if desde:
        query = query.filter(Relevamiento.fecha >= desde)
    if hasta:
        query = query.filter(Relevamiento.fecha <= hasta)
    return query


def _domicilios_pendientes_query(filters: RelevamientosPendientesFilters):
    query = (
        Relevamiento.query.join(Domicilio, Relevamiento.domicilio_id == Domicilio.id)
        .filter(Domicilio.deleted_at.is_(None))
        .filter(or_(Domicilio.calle_norm_status.is_(None), Domicilio.calle_norm_status != "OK"))
    )
    return _apply_fecha(query, filters.desde, filters.hasta)


def get_pendientes_summary(filters: RelevamientosPendientesFilters) -> Dict[str, int]:
    """
    Obtiene conteos de pendientes de Relevamientos (domicilios).
    """
    domicilios = _domicilios_pendientes_query(filters).count()
    total = domicilios
    return {"total": total, "domicilios": domicilios}


def get_pendientes_list(filters: RelevamientosPendientesFilters) -> List[Relevamiento]:
    """
    Lista relevamientos pendientes según tipo.
    """
    if filters.tipo != "domicilios":
        return []
    query = _domicilios_pendientes_query(filters)
    return query.order_by(Relevamiento.id.desc()).all()
