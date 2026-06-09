from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query, joinedload

from app.database import db
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    resolve_domicilio_efectivo_para_iniciador,
)
from app.models import Domicilio, IniciadorRuta, Relevamiento, RutaItem, RutaTrabajo


def assert_ruta_borrador_para_planificacion(ruta_id: int) -> RutaTrabajo:
    """
    Valida que la ruta exista y esté en BORRADOR para operaciones de planificación.

    Raises:
        LookupError: ruta inexistente.
        RuntimeError: ruta no en BORRADOR.
    """
    ruta = RutaTrabajo.query.get(ruta_id)
    if not ruta:
        raise LookupError("Ruta de trabajo no encontrada")
    if ruta.estado_ruta != "BORRADOR":
        raise RuntimeError("La ruta debe estar en BORRADOR para listar iniciadores pendientes")
    return ruta


def planificable_iniciadores_base_query() -> Query:
    """
    Query base: iniciadores PENDIENTE, no eliminados, no asignados a ítem activo en ruta BORRADOR.

    Requiere llamar antes assert_ruta_borrador_para_planificacion si se necesita validar ruta.
    """
    return (
        IniciadorRuta.query.outerjoin(Domicilio, Domicilio.id == IniciadorRuta.domicilio_id)
        .options(
            joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.rubro),
            joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.calle_catalogo),
            joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.distrito),
            joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.geocode),
            joinedload(IniciadorRuta.relevamiento).joinedload(Relevamiento.rubro),
        )
        .filter(
            IniciadorRuta.estado_iniciador == "PENDIENTE",
            IniciadorRuta.deleted_at.is_(None),
            ~IniciadorRuta.ruta_items.any(
                (RutaItem.deleted_at.is_(None))
                & (RutaItem.ruta_trabajo.has(RutaTrabajo.estado_ruta == "BORRADOR"))
            ),
        )
    )


def _orden_planificacion_sql(orden: str | None) -> tuple:
    """
    Orden para listados M4 / Planificación.

    Valores: prioridad (default), fecha_asc, fecha_desc, prioridad_asc.
    """

    o = (orden or "prioridad").strip().lower()
    if o == "fecha_asc":
        return (
            IniciadorRuta.fecha_origen.asc(),
            IniciadorRuta.prioridad.desc(),
            IniciadorRuta.id.asc(),
        )
    if o == "fecha_desc":
        return (
            IniciadorRuta.fecha_origen.desc(),
            IniciadorRuta.prioridad.desc(),
            IniciadorRuta.id.asc(),
        )
    if o == "prioridad_asc":
        return (
            IniciadorRuta.prioridad.asc(),
            IniciadorRuta.fecha_origen.asc(),
            IniciadorRuta.id.asc(),
        )
    return (
        IniciadorRuta.prioridad.desc(),
        IniciadorRuta.fecha_origen.asc(),
        IniciadorRuta.id.asc(),
    )


def get_iniciadores_pendientes_para_ruta(
    *,
    ruta_id: int,
    tipo: str | None,
    prioridad: int | None,
    prioridad_categoria: str | None,
    distrito: int | None,
    q: str | None,
    turno_sugerido: str | None,
    calle_catalogo_id: int | None,
    page: int,
    per_page: int,
    orden_planificacion: bool = False,
    planificacion_orden: str | None = None,
) -> tuple[list[IniciadorRuta], int]:
    """
    Lista iniciadores planificables para una ruta en BORRADOR.

    Reglas:
    - ruta debe existir y estar en BORRADOR.
    - solo iniciadores PENDIENTE y no soft-deleted.
    - excluye iniciadores ya tomados por RutaItem no eliminado de rutas activas.
    - para slice 1, ruta activa = BORRADOR.
    - filtros opcionales: tipo, prioridad, distrito, calle_catalogo_id (domicilio), q, turno_sugerido.

    Returns:
    - tupla (items, total)

    Raises:
    - LookupError: si ruta no existe.
    - RuntimeError: si ruta no está en BORRADOR.
    """
    assert_ruta_borrador_para_planificacion(ruta_id)

    query = planificable_iniciadores_base_query()

    if tipo:
        query = query.filter(IniciadorRuta.tipo_iniciador == tipo)
    if prioridad_categoria == "BAJA":
        query = query.filter(IniciadorRuta.prioridad == 1)
    elif prioridad_categoria == "MEDIA":
        query = query.filter(IniciadorRuta.prioridad == 2)
    elif prioridad_categoria == "ALTA":
        query = query.filter(IniciadorRuta.prioridad >= 3)
    elif prioridad is not None:
        query = query.filter(IniciadorRuta.prioridad == prioridad)
    if calle_catalogo_id is not None:
        query = query.filter(Domicilio.calle_catalogo_id == calle_catalogo_id)
    if turno_sugerido:
        query = query.filter(IniciadorRuta.turno_sugerido == turno_sugerido)
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                Domicilio.calle.ilike(term),
                Domicilio.numero.ilike(term),
                IniciadorRuta.observaciones.ilike(term),
            )
        )

    if orden_planificacion:
        order = _orden_planificacion_sql(planificacion_orden)
    else:
        order = (
            IniciadorRuta.fecha_origen.asc(),
            IniciadorRuta.prioridad.asc(),
            IniciadorRuta.id.asc(),
        )

    if distrito is not None:
        candidatos = query.order_by(*order).all()
        filtrados: list[IniciadorRuta] = []
        for ini in candidatos:
            efectivo = resolve_domicilio_efectivo_para_iniciador(
                ini,
                apply_backfill=True,
                try_sync=True,
            )
            dom_ef = db.session.get(Domicilio, efectivo.domicilio_id) if efectivo.domicilio_id else None
            if dom_ef and dom_ef.distrito_id == distrito:
                filtrados.append(ini)
        total = len(filtrados)
        start = (page - 1) * per_page
        items = filtrados[start : start + per_page]
        db.session.commit()
        return items, total

    total = query.count()
    items = (
        query.order_by(*order)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    for ini in items:
        resolve_domicilio_efectivo_para_iniciador(ini, apply_backfill=True, try_sync=True)
    db.session.commit()
    return items, total
