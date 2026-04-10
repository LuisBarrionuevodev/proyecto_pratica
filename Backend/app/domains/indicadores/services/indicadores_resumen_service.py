from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import and_, extract, func

from app.database import db
from app.domains.indicadores.schemas.resumen_out import (
    ActasPorTipo,
    ActuacionesResumen,
    ContraproducenciaTopItem,
    DecomisoKgPorMesItem,
    DecomisoKgResumen,
    IndicadoresResumenOut,
    RubroTopItem,
    RutaItemsEjecucionResumen,
)
from app.models import (
    Actuaciones,
    Clausura,
    Decomiso,
    Domicilio,
    Inspeccion,
    Rubro,
    RutaItem,
    RutaTrabajo,
    actuaciones_inspector,
)

_TOP_RUBROS_LIMIT = 10


def _float_kg(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def _actuacion_ids_subquery(
    desde: date,
    hasta: date,
    distrito_id: Optional[int],
    inspector_id: Optional[int],
):
    """
    Subconsulta de IDs de actuaciones en rango de fecha con filtros opcionales.

    Parámetros:
        desde, hasta: rango inclusive sobre `Actuaciones.fecha`.
        distrito_id: join por domicilio; excluye actuaciones sin domicilio o de otro distrito.
        inspector_id: join por `actuaciones_inspector` con `deleted_at` nulo.

    Retorno:
        Subquery con columna `id`.
    """
    q = db.session.query(Actuaciones.id).filter(
        Actuaciones.fecha >= desde,
        Actuaciones.fecha <= hasta,
    )
    if distrito_id is not None:
        q = q.join(Domicilio, Domicilio.id == Actuaciones.domicilio_id).filter(
            Domicilio.distrito_id == distrito_id
        )
    if inspector_id is not None:
        q = q.join(
            actuaciones_inspector,
            actuaciones_inspector.c.actuaciones_id == Actuaciones.id,
        ).filter(
            actuaciones_inspector.c.inspector_id == inspector_id,
            actuaciones_inspector.c.deleted_at.is_(None),
        )
    return q.distinct().subquery("act_indicadores_filtered")


def _has_contraproducencia_expr():
    return and_(
        Actuaciones.contraproducencia.isnot(None),
        func.trim(Actuaciones.contraproducencia) != "",
    )


def _ruta_items_ejecucion_por_fecha_ruta(
    desde: date,
    hasta: date,
) -> RutaItemsEjecucionResumen:
    """
    Agrega ítems de ruta por `RutaTrabajo.fecha` (sin turno ni filtros de distrito/inspector).

    Parámetros:
        desde, hasta: rango inclusive sobre fecha de la ruta.

    Retorno:
        Conteos totales y por `estado_ejecucion` (REALIZADO / NO_REALIZADO / sin clasificar).
    """
    rows = (
        db.session.query(RutaItem.estado_ejecucion, func.count(RutaItem.id))
        .join(RutaTrabajo, RutaTrabajo.id == RutaItem.ruta_trabajo_id)
        .filter(
            RutaTrabajo.fecha >= desde,
            RutaTrabajo.fecha <= hasta,
            RutaItem.deleted_at.is_(None),
        )
        .group_by(RutaItem.estado_ejecucion)
        .all()
    )
    realizado = 0
    no_realizado = 0
    sin = 0
    total = 0
    for estado, cnt in rows:
        total += int(cnt)
        if estado is None:
            sin += int(cnt)
        elif estado == "REALIZADO":
            realizado += int(cnt)
        elif estado == "NO_REALIZADO":
            no_realizado += int(cnt)
        else:
            sin += int(cnt)
    return RutaItemsEjecucionResumen(
        total=total,
        estado_ejecucion_realizado=realizado,
        estado_ejecucion_no_realizado=no_realizado,
        estado_ejecucion_sin_clasificar=sin,
    )


def build_indicadores_resumen(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> IndicadoresResumenOut:
    """
    Calcula agregados del dashboard para el periodo y filtros dados.

    Parámetros:
        desde, hasta: fechas inclusive sobre `Actuaciones.fecha`.
        distrito_id, inspector_id: filtros opcionales sobre el conjunto de actuaciones.

    Retorno:
        `IndicadoresResumenOut` listo para serializar JSON.

    Notas:
        El bloque `ruta_items_ejecucion` usa solo fechas de `ruta_trabajo` (mismo rango de
        calendario que el query), sin aplicar distrito ni inspector.
        `top_rubros` cuenta actuaciones con `domicilio_id` y `domicilio.rubro_id` no nulos;
        el resto no aparece en el ranking (no se duplica fila por inspectores: subquery `distinct`).
    """
    sq = _actuacion_ids_subquery(desde, hasta, distrito_id, inspector_id)
    has_contra = _has_contraproducencia_expr()

    total = db.session.query(func.count()).select_from(sq).scalar() or 0
    total = int(total)

    con_cp = (
        db.session.query(func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(has_contra)
        .scalar()
        or 0
    )
    con_cp = int(con_cp)
    sin_cp = max(0, total - con_cp)

    top_rows = (
        db.session.query(Actuaciones.contraproducencia, func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(has_contra)
        .group_by(Actuaciones.contraproducencia)
        .order_by(func.count(Actuaciones.id).desc())
        .limit(10)
        .all()
    )
    contraproducencias_top = [
        ContraproducenciaTopItem(valor=str(v), count=int(c)) for v, c in top_rows
    ]

    n_insp = (
        db.session.query(func.count(Inspeccion.id))
        .join(sq, sq.c.id == Inspeccion.actuacion_id)
        .scalar()
        or 0
    )
    n_notif = (
        db.session.query(func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(Actuaciones.notificacion_id.isnot(None))
        .scalar()
        or 0
    )
    n_comp = (
        db.session.query(func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(Actuaciones.comprobacion_id.isnot(None))
        .scalar()
        or 0
    )
    n_clau = (
        db.session.query(func.count(Clausura.id))
        .join(sq, sq.c.id == Clausura.actuacion_id)
        .scalar()
        or 0
    )
    n_deco = (
        db.session.query(func.count(Decomiso.id))
        .join(sq, sq.c.id == Decomiso.actuacion_id)
        .scalar()
        or 0
    )

    rubro_rows = (
        db.session.query(Rubro.id, Rubro.nombre, func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .join(Domicilio, Domicilio.id == Actuaciones.domicilio_id)
        .join(Rubro, Rubro.id == Domicilio.rubro_id)
        .group_by(Rubro.id, Rubro.nombre)
        .order_by(func.count(Actuaciones.id).desc())
        .limit(_TOP_RUBROS_LIMIT)
        .all()
    )
    top_rubros = [
        RubroTopItem(rubro_id=int(rid), nombre=str(nombre), count=int(cnt))
        for rid, nombre, cnt in rubro_rows
    ]

    sum_kg = (
        db.session.query(func.sum(Decomiso.cantidad))
        .join(sq, sq.c.id == Decomiso.actuacion_id)
        .scalar()
    )
    total_kg = _float_kg(sum_kg)

    ym_rows = (
        db.session.query(
            extract("year", Actuaciones.fecha),
            extract("month", Actuaciones.fecha),
            func.sum(Decomiso.cantidad),
        )
        .select_from(Decomiso)
        .join(sq, sq.c.id == Decomiso.actuacion_id)
        .join(Actuaciones, Actuaciones.id == Decomiso.actuacion_id)
        .group_by(
            extract("year", Actuaciones.fecha),
            extract("month", Actuaciones.fecha),
        )
        .order_by(
            extract("year", Actuaciones.fecha),
            extract("month", Actuaciones.fecha),
        )
        .all()
    )
    por_mes = [
        DecomisoKgPorMesItem(
            anio=int(y),
            mes=int(m),
            kg=_float_kg(kg),
        )
        for y, m, kg in ym_rows
    ]
    decomiso_kg = DecomisoKgResumen(total_kg=total_kg, por_mes=por_mes)

    ruta_part = _ruta_items_ejecucion_por_fecha_ruta(desde, hasta)

    return IndicadoresResumenOut(
        periodo={"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        filtros={
            "distrito_id": distrito_id,
            "inspector_id": inspector_id,
        },
        actuaciones=ActuacionesResumen(
            total=total,
            con_contraproducencia=con_cp,
            sin_contraproducencia=sin_cp,
        ),
        contraproducencias_top=contraproducencias_top,
        actas_por_tipo=ActasPorTipo(
            inspeccion=int(n_insp),
            notificacion=int(n_notif),
            comprobacion=int(n_comp),
            clausura=int(n_clau),
            decomiso=int(n_deco),
        ),
        ruta_items_ejecucion=ruta_part,
        top_rubros=top_rubros,
        decomiso_kg=decomiso_kg,
    )
