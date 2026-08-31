"""
Listado paginado de fichas ``establecimiento_operativo`` con filtros sobre domicilio/contribuyente.

FIX.7: deduplica por identidad lógica (contribuyente + domicilio); una fila por business key.
"""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    agrupar_eo_por_identidad_logica,
    rubro_vigente_identidad_logica,
    seleccionar_eo_canonico_del_grupo,
)
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
    Lista fichas operativas deduplicadas por identidad lógica, paginadas.

    Parámetros:
        page: página 1-based.
        page_size: tamaño de página (acotado por el caller).
        calle: subcadena sobre ``domicilio.calle`` (opcional).
        contrib: subcadena en apellido, nombre, razón social o documento (opcional).
        distrito_id: filtro por ``domicilio.distrito_id``.
        rubro_id: filtro por ``domicilio.rubro_id`` (no forma parte de identidad lógica).

    Retorno:
        Tupla (items canónicos de la página, total de fichas lógicas).

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

    q = q.options(
        joinedload(EstablecimientoOperativo.domicilio).joinedload(Domicilio.contribuyente),
        joinedload(EstablecimientoOperativo.domicilio).joinedload(Domicilio.rubro),
        joinedload(EstablecimientoOperativo.domicilio).joinedload(Domicilio.distrito),
        joinedload(EstablecimientoOperativo.domicilio).joinedload(Domicilio.calle_catalogo),
    )

    all_items = q.all()
    groups = agrupar_eo_por_identidad_logica(all_items)
    canonical: list[EstablecimientoOperativo] = []
    for eos in groups.values():
        canon = seleccionar_eo_canonico_del_grupo(eos)
        dom = canon.domicilio
        if dom is not None:
            canon._rubro_vigente_listado = rubro_vigente_identidad_logica(dom)  # type: ignore[attr-defined]
        canonical.append(canon)

    canonical.sort(key=lambda e: int(e.id), reverse=True)
    total = len(canonical)
    offset = (page - 1) * page_size
    items = canonical[offset : offset + page_size]
    return items, total
