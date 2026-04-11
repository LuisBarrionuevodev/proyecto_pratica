"""
Listado paginado de fichas ``establecimiento_operativo`` con filtros sobre domicilio/contribuyente.
"""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.database import db
from app.models import Contribuyente, Domicilio, EstablecimientoOperativo


def list_establecimientos_operativos(
    *,
    page: int = 1,
    page_size: int = 20,
    calle: str | None = None,
    contrib: str | None = None,
    distrito_id: int | None = None,
    rubro_id: int | None = None,
) -> tuple[list[EstablecimientoOperativo], int]:
    """
    Lista fichas operativas con domicilio no eliminado, paginadas.

    Parámetros:
        page: página 1-based.
        page_size: tamaño de página (acotado por el caller).
        calle: subcadena sobre ``domicilio.calle`` (opcional).
        contrib: subcadena en apellido, nombre, razón social o documento (opcional).
        distrito_id: filtro por ``domicilio.distrito_id``.
        rubro_id: filtro por ``domicilio.rubro_id``.

    Retorno:
        Tupla (items de la página, total de filas que cumplen filtros).

    Errores:
        Ninguno; total 0 si no hay datos.
    """
    q = EstablecimientoOperativo.query.join(
        Domicilio, EstablecimientoOperativo.domicilio_id == Domicilio.id
    ).filter(Domicilio.deleted_at.is_(None))

    if distrito_id is not None:
        q = q.filter(Domicilio.distrito_id == distrito_id)
    if rubro_id is not None:
        q = q.filter(Domicilio.rubro_id == rubro_id)

    if calle and calle.strip():
        term = f"%{calle.strip()}%"
        q = q.filter(Domicilio.calle.like(term))

    if contrib and contrib.strip():
        term = f"%{contrib.strip()}%"
        q = q.join(Contribuyente, Domicilio.contribuyente_id == Contribuyente.id).filter(
            or_(
                Contribuyente.apellido.like(term),
                Contribuyente.nombre.like(term),
                Contribuyente.razon_social.like(term),
                Contribuyente.documento.like(term),
            )
        )

    total = q.order_by(None).count()

    q = q.options(
        joinedload(EstablecimientoOperativo.domicilio).joinedload(Domicilio.contribuyente),
        joinedload(EstablecimientoOperativo.domicilio).joinedload(Domicilio.rubro),
        joinedload(EstablecimientoOperativo.domicilio).joinedload(Domicilio.distrito),
    ).order_by(EstablecimientoOperativo.id.desc())
    offset = (page - 1) * page_size
    items = q.offset(offset).limit(page_size).all()

    return items, total
