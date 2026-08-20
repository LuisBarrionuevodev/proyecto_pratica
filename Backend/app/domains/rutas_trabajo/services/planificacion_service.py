"""
Servicios para Planificación MVP: métricas (M1), carga por distrito (M2), urgentes (M3).

M4 reutiliza get_iniciadores_pendientes_para_ruta con distrito obligatorio.
"""

from __future__ import annotations

import time

from sqlalchemy import func

from app.database import db
from app.models import Domicilio, Distrito, IniciadorRuta
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    assert_ruta_borrador_para_planificacion,
    get_iniciadores_pendientes_para_ruta,
    planificable_iniciadores_base_query,
    _enriquecer_domicilio_efectivo_pagina,
)
from app.domains.rutas_trabajo.utils.urgentes_filtros import apply_urgentes_filtros
from app.domains.rutas_trabajo.utils.planificacion_debug import medir_oper_ruta_7d
from app.domains.rutas_trabajo.utils.planificacion_m4_sql import apply_sql_exclusion_pool_y_ruta_activa

_MAX_PER_PAGE_URGENTES = 100

# Desglose "Oficios urgentes" en cards: tipos derivados de oficio (no incluye notificación).
TIPOS_OFICIO_METRICA: tuple[str, ...] = (
    "REINSPECCION_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)


def _query_planificable_filtrada_por_distrito(
    ruta_id: int,
    distrito_id: int | None,
):
    """
    Query planificable opcionalmente restringida a un distrito (domicilio).
    """
    assert_ruta_borrador_para_planificacion(ruta_id)
    q = planificable_iniciadores_base_query()
    if distrito_id is not None:
        q = q.filter(Domicilio.distrito_id == distrito_id)
    return q


def get_planificacion_metricas(ruta_id: int, distrito_id: int | None) -> dict:
    """
    M1: conteos para cards. Si distrito_id, métricas solo en ese distrito.

    Retorno:
        dict con keys: total, alta, oficios_urgentes, denuncias, notificaciones, relevamientos
    """
    total = _query_planificable_filtrada_por_distrito(ruta_id, distrito_id).count()
    base = _query_planificable_filtrada_por_distrito
    # Alta prioridad operativa: P3+, excluye RELEVAMIENTO (aunque un reingreso suba número en DB).
    alta = (
        base(ruta_id, distrito_id)
        .filter(
            IniciadorRuta.prioridad >= 3,
            IniciadorRuta.tipo_iniciador != "RELEVAMIENTO",
        )
        .count()
    )
    oficios_urgentes = (
        base(ruta_id, distrito_id)
        .filter(IniciadorRuta.tipo_iniciador.in_(TIPOS_OFICIO_METRICA))
        .count()
    )
    denuncias = (
        base(ruta_id, distrito_id).filter(IniciadorRuta.tipo_iniciador == "DENUNCIA").count()
    )
    notificaciones = (
        base(ruta_id, distrito_id)
        .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION")
        .count()
    )
    relevamientos = (
        base(ruta_id, distrito_id)
        .filter(IniciadorRuta.tipo_iniciador == "RELEVAMIENTO")
        .count()
    )
    return {
        "total": total,
        "alta": alta,
        "oficios_urgentes": oficios_urgentes,
        "denuncias": denuncias,
        "notificaciones": notificaciones,
        "relevamientos": relevamientos,
    }


def get_carga_por_distritos(ruta_id: int) -> list[dict]:
    """
    M2: cantidad de iniciadores planificables por distrito (para coropleta).

    Retorno:
        lista de { distrito_id, distrito_nombre, cantidad }
    """
    assert_ruta_borrador_para_planificacion(ruta_id)
    rows = (
        planificable_iniciadores_base_query()
        .join(Distrito, Distrito.id == Domicilio.distrito_id)
        .filter(Domicilio.distrito_id.isnot(None))
        .with_entities(Domicilio.distrito_id, Distrito.nombre, func.count(IniciadorRuta.id))
        .group_by(Domicilio.distrito_id, Distrito.nombre)
        .order_by(Distrito.nombre.asc())
        .all()
    )
    return [
        {"distrito_id": r[0], "distrito_nombre": r[1] or "", "cantidad": int(r[2])}
        for r in rows
    ]


def get_planificacion_urgentes(
    ruta_id: int,
    *,
    page: int,
    per_page: int,
    distrito_id: int | None = None,
    tipo_urgente: str | None = None,
    q: str | None = None,
    numero_oficio: str | None = None,
    numero_comprobacion: str | None = None,
    q_identificador: str | None = None,
    q_domicilio: str | None = None,
    rubro_id: int | None = None,
) -> tuple[list, int]:
    """
    M3: bandeja urgentes — elegible_urgente (tipo != RELEVAMIENTO y prioridad >= 3).

    Si ``distrito_id`` se informa, el universo coincide con M1 (métrica ``alta``) para ese distrito
    (domicilio FK del iniciador, no domicilio efectivo M4).

    Solo incluye iniciadores agregables (OPER-RUTA.6I/6J): sin pool/ruta activa en ninguna ruta.

    OPER-RUTA.7D: filtros SQL + paginación real + exclusiones NOT EXISTS (reutiliza 7B).

    Orden: prioridad DESC, fecha_origen ASC, id ASC.

    Retorno:
        (lista IniciadorRuta, total)
    """
    assert_ruta_borrador_para_planificacion(ruta_id)
    per_page = min(int(per_page), _MAX_PER_PAGE_URGENTES)
    order = (
        IniciadorRuta.prioridad.desc(),
        IniciadorRuta.fecha_origen.asc(),
        IniciadorRuta.id.asc(),
    )

    with medir_oper_ruta_7d(
        "URGENTES",
        ruta=ruta_id,
        page=page,
        per_page=per_page,
        distrito=distrito_id if distrito_id is not None else "",
    ) as dbg:
        query = planificable_iniciadores_base_query().filter(
            IniciadorRuta.tipo_iniciador != "RELEVAMIENTO",
            IniciadorRuta.prioridad >= 3,
        )
        if distrito_id is not None:
            query = query.filter(Domicilio.distrito_id == int(distrito_id))
        query = apply_urgentes_filtros(
            query,
            tipo_urgente=tipo_urgente,
            q=q,
            numero_oficio=numero_oficio,
            numero_comprobacion=numero_comprobacion,
            q_identificador=q_identificador,
            q_domicilio=q_domicilio,
            rubro_id=rubro_id,
        )
        query = apply_sql_exclusion_pool_y_ruta_activa(query)

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


def get_planificacion_pendientes_contexto(
    ruta_id: int,
    *,
    distrito_id: int,
    tipo: str | None,
    prioridad: int | None,
    prioridad_categoria: str | None,
    q: str | None,
    turno_sugerido: str | None,
    calle_catalogo_id: int | None,
    page: int,
    per_page: int,
    orden: str | None = None,
) -> tuple[list, int]:
    """
    M4: mismo universo que iniciadores-pendientes pero distrito obligatorio y orden Planificación.
    """
    return get_iniciadores_pendientes_para_ruta(
        ruta_id=ruta_id,
        tipo=tipo,
        prioridad=prioridad,
        prioridad_categoria=prioridad_categoria,
        distrito=distrito_id,
        q=q,
        turno_sugerido=turno_sugerido,
        calle_catalogo_id=calle_catalogo_id,
        page=page,
        per_page=per_page,
        orden_planificacion=True,
        planificacion_orden=orden,
        solo_agregables_ruta=True,
    )
