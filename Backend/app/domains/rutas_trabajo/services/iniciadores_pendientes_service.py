from __future__ import annotations

import time

from sqlalchemy import or_
from sqlalchemy.orm import Query, joinedload

from app.database import db
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    resolve_domicilio_efectivo_para_iniciador,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_eligibility_service import (
    filtrar_iniciadores_agregables_a_ruta,
)
from app.domains.rutas_trabajo.utils.planificacion_debug import medir_oper_ruta_7a, medir_oper_ruta_7b
from app.domains.rutas_trabajo.utils.planificacion_m4_sql import (
    apply_joins_y_filtro_distrito_efectivo,
    apply_sql_exclusion_pool_y_ruta_activa,
)
from app.models import Domicilio, IniciadorRuta, Notificacion, Oficio, Relevamiento, RutaItem, RutaTrabajo

_MAX_PER_PAGE_M4 = 500


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

    No excluye iniciadores reencolados con visitas previas FINALIZADO+REALIZADO (p. ej. oficio NO_CUMPLE):
    el filtro operativo es ``estado_iniciador == PENDIENTE``.

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
            joinedload(IniciadorRuta.denuncia),
            joinedload(IniciadorRuta.oficio).options(
                joinedload(Oficio.comprobacion),
                joinedload(Oficio.juzgado),
                joinedload(Oficio.expediente),
            ),
            joinedload(IniciadorRuta.notificacion).joinedload(Notificacion.expedientes),
            joinedload(IniciadorRuta.comprobacion),
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


def _aplicar_filtros_opcionales(
    query: Query,
    *,
    tipo: str | None,
    prioridad: int | None,
    prioridad_categoria: str | None,
    q: str | None,
    turno_sugerido: str | None,
    calle_catalogo_id: int | None,
) -> Query:
    """Filtros SQL opcionales sobre query base (domicilio FK del iniciador)."""
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
    return query


def _enriquecer_domicilio_efectivo_pagina(items: list[IniciadorRuta]) -> None:
    """Backfill/sync domicilio efectivo solo para la página devuelta."""
    for ini in items:
        resolve_domicilio_efectivo_para_iniciador(ini, apply_backfill=True, try_sync=True)


def _get_iniciadores_pendientes_m4_optimizado(
    *,
    ruta_id: int,
    tipo: str | None,
    prioridad: int | None,
    prioridad_categoria: str | None,
    distrito: int,
    q: str | None,
    turno_sugerido: str | None,
    calle_catalogo_id: int | None,
    page: int,
    per_page: int,
    planificacion_orden: str | None,
) -> tuple[list[IniciadorRuta], int]:
    """
    M4 optimizado (OPER-RUTA.7B): filtros SQL, paginación real, exclusiones NOT EXISTS.

    Sin ``.all()`` masivo ni filtro distrito/elegibilidad en Python sobre el universo completo.
    """
    per_page = min(int(per_page), _MAX_PER_PAGE_M4)
    order = _orden_planificacion_sql(planificacion_orden)

    with medir_oper_ruta_7b(
        "M4",
        ruta=ruta_id,
        distrito=distrito,
        page=page,
        per_page=per_page,
    ) as dbg:
        query = planificable_iniciadores_base_query()
        query = _aplicar_filtros_opcionales(
            query,
            tipo=tipo,
            prioridad=prioridad,
            prioridad_categoria=prioridad_categoria,
            q=q,
            turno_sugerido=turno_sugerido,
            calle_catalogo_id=calle_catalogo_id,
        )
        query = apply_sql_exclusion_pool_y_ruta_activa(query)
        query = apply_joins_y_filtro_distrito_efectivo(query, int(distrito))

        t_count = time.perf_counter()
        total = query.count()
        dbg["count_ms"] = int((time.perf_counter() - t_count) * 1000)
        dbg["total"] = total
        dbg["rows_page"] = 0

        t_sql = time.perf_counter()
        items = (
            query.order_by(*order)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        dbg["sql_ms"] = int((time.perf_counter() - t_sql) * 1000)
        dbg["rows_page"] = len(items)

        t_enrich = time.perf_counter()
        _enriquecer_domicilio_efectivo_pagina(items)
        dbg["enrich_ms"] = int((time.perf_counter() - t_enrich) * 1000)

        db.session.commit()
        return items, total


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
    solo_agregables_ruta: bool = False,
) -> tuple[list[IniciadorRuta], int]:
    """
    Lista iniciadores planificables para una ruta en BORRADOR.

    Reglas:
    - ruta debe existir y estar en BORRADOR.
    - solo iniciadores PENDIENTE y no soft-deleted.
    - excluye iniciadores ya tomados por RutaItem no eliminado de rutas activas.
    - para slice 1, ruta activa = BORRADOR.
    - filtros opcionales: tipo, prioridad, distrito, calle_catalogo_id (domicilio), q, turno_sugerido.
    - solo_agregables_ruta: excluye iniciadores en pool/ruta activa (mapa M4).

    Returns:
    - tupla (items, total)

    Raises:
    - LookupError: si ruta no existe.
    - RuntimeError: si ruta no está en BORRADOR.
    """
    assert_ruta_borrador_para_planificacion(ruta_id)

    if solo_agregables_ruta and distrito is not None and orden_planificacion:
        return _get_iniciadores_pendientes_m4_optimizado(
            ruta_id=ruta_id,
            tipo=tipo,
            prioridad=prioridad,
            prioridad_categoria=prioridad_categoria,
            distrito=int(distrito),
            q=q,
            turno_sugerido=turno_sugerido,
            calle_catalogo_id=calle_catalogo_id,
            page=page,
            per_page=per_page,
            planificacion_orden=planificacion_orden,
        )

    with medir_oper_ruta_7a(
        "M4",
        ruta=ruta_id,
        distrito=distrito if distrito is not None else "",
        page=page,
        per_page=per_page,
        solo_agregables=int(solo_agregables_ruta),
    ) as dbg:
        query = planificable_iniciadores_base_query()

        query = _aplicar_filtros_opcionales(
            query,
            tipo=tipo,
            prioridad=prioridad,
            prioridad_categoria=prioridad_categoria,
            q=q,
            turno_sugerido=turno_sugerido,
            calle_catalogo_id=calle_catalogo_id,
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
            t_sql = time.perf_counter()
            candidatos = query.order_by(*order).all()
            dbg["rows_base"] = len(candidatos)
            dbg["sql_fetch_ms"] = int((time.perf_counter() - t_sql) * 1000)
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
            dbg["rows_distrito"] = len(filtrados)
            pre_ag = len(filtrados)
            if solo_agregables_ruta:
                filtrados = filtrar_iniciadores_agregables_a_ruta(filtrados, ruta_id)
            dbg["rows_final"] = len(filtrados)
            dbg["descartados_agregables"] = pre_ag - len(filtrados)
            total = len(filtrados)
            start = (page - 1) * per_page
            items = filtrados[start : start + per_page]
            db.session.commit()
            return items, total

        if solo_agregables_ruta:
            query = apply_sql_exclusion_pool_y_ruta_activa(query)
            t_count = time.perf_counter()
            total = query.count()
            dbg["count_ms"] = int((time.perf_counter() - t_count) * 1000)
            dbg["rows_final"] = total
            t_sql = time.perf_counter()
            items = (
                query.order_by(*order)
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            dbg["sql_fetch_ms"] = int((time.perf_counter() - t_sql) * 1000)
            _enriquecer_domicilio_efectivo_pagina(items)
            db.session.commit()
            return items, total

        total = query.count()
        items = (
            query.order_by(*order)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        _enriquecer_domicilio_efectivo_pagina(items)
        db.session.commit()
        return items, total
