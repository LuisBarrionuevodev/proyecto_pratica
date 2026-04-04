from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import and_, exists, func

from app.database import db
from app.models import Relevamiento, Inspector, Domicilio, IniciadorRuta
from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters


def _apply_common_filters(query, filters: RelevamientosListFilters):
    """Aplica filtros compartidos para listados de relevamientos."""
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
        query = query.join(Domicilio, Relevamiento.domicilio_id == Domicilio.id).filter(
            Domicilio.deleted_at.is_(None)
        )
        if filters.calle:
            query = query.filter(func.upper(Domicilio.calle).like(f"%{filters.calle.upper()}%"))
        if filters.numero:
            query = query.filter(Domicilio.numero == str(filters.numero).strip())
    return query


def listar_relevamientos_con_filtros(filters: RelevamientosListFilters) -> Dict[str, Any]:
    """
    Lista relevamientos aplicando filtros y paginación.

    Args:
        filters: filtros validados (desde, hasta, inspector, calle, numero).

    Returns:
        dict con items y meta.
    """
    query = Relevamiento.query.filter(Relevamiento.deleted_at.is_(None))

    query = _apply_common_filters(query, filters)

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


def listar_relevamientos_realizados_actuacion_completada_con_filtros(
    filters: RelevamientosListFilters,
) -> Dict[str, Any]:
    """
    Lista relevamientos con cierre operativo exitoso vía ruta (Completar trabajo, visita realizada).

    Criterio conservador:
    - existe ``IniciadorRuta`` tipo ``RELEVAMIENTO``, no borrado, con ``estado_iniciador == CUMPLIDO``
      (cierre exitoso vía Completar trabajo; la actuación vive en el ítem de ruta, no necesariamente en ``iniciador.actuacion_id``).

    Args:
        filters: filtros de fecha/inspector/calle/número y paginación.

    Returns:
        dict con ``items`` (``Relevamiento``) y ``meta``.
    """
    ir = IniciadorRuta
    # Nota: al publicar ruta la actuación queda en `ruta_item.actuacion_id`; el ORM no copia
    # `actuacion_id` al iniciador. CUMPLIDO tras Completar trabajo implica cierre con actuación en el ítem.
    cumplido_operativo = exists().where(
        and_(
            ir.relevamiento_id == Relevamiento.id,
            ir.tipo_iniciador == "RELEVAMIENTO",
            ir.estado_iniciador == "CUMPLIDO",
            ir.deleted_at.is_(None),
        )
    )
    query = Relevamiento.query.filter(
        Relevamiento.deleted_at.is_(None),
        cumplido_operativo,
    )

    query = _apply_common_filters(query, filters)

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


def listar_relevamientos_operativos_con_filtros(filters: RelevamientosListFilters) -> Dict[str, Any]:
    """
    Lista relevamientos operativos:
    solo aquellos con iniciador_ruta RELEVAMIENTO en estado PENDIENTE y activo.
    """
    pending_iniciador_subq = (
        db.session.query(
            IniciadorRuta.relevamiento_id.label("relevamiento_id"),
            func.max(IniciadorRuta.id).label("iniciador_id"),
        )
        .filter(
            IniciadorRuta.relevamiento_id.isnot(None),
            IniciadorRuta.tipo_iniciador == "RELEVAMIENTO",
            IniciadorRuta.estado_iniciador == "PENDIENTE",
            IniciadorRuta.deleted_at.is_(None),
        )
        .group_by(IniciadorRuta.relevamiento_id)
        .subquery()
    )

    query = (
        db.session.query(Relevamiento, IniciadorRuta)
        .join(pending_iniciador_subq, pending_iniciador_subq.c.relevamiento_id == Relevamiento.id)
        .join(IniciadorRuta, IniciadorRuta.id == pending_iniciador_subq.c.iniciador_id)
        .filter(Relevamiento.deleted_at.is_(None))
    )

    query = _apply_common_filters(query, filters)

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
