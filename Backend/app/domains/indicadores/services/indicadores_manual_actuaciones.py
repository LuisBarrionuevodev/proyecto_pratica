"""
Actuaciones de Cargar actuación (sin RutaItem propio) para indicadores.

Criterio V1.1-INDICADORES-CLASIFICACION.1:
- Período: ``Actuaciones.fecha`` (no ``RutaTrabajo.fecha``).
- Excluye filas cuya OT ya tiene un cierre de ruta REALIZADO o NO_REALIZADO
  (unicidad por OT; reinspecciones con OT distinta se cuentan aparte).
- Realizada: sin contraproducencia efectiva (vacío / NO_HUBO).
- No realizada: contraproducencia que cuenta (misma exclusión que indicadores).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import exists, func, or_, select, union
from sqlalchemy.orm import aliased

from app.database import db
from app.domains.indicadores.services.indicadores_no_realizadas_queries import (
    is_contraproducencia_excluida_valor,
)
from app.domains.indicadores.services.indicadores_resumen_service import (
    _has_contraproducencia_expr,
)
from app.models import Actuaciones, Domicilio, IniciadorRuta, RutaItem, RutaTrabajo, actuaciones_inspector


def _cierre_ruta_por_ot_exists(
    *,
    estados_ejecucion: tuple[str, ...],
    desde: date,
    hasta: date,
):
    """
    EXISTS: hay RutaItem de ruta PUBLICADA con esa OT y esos estados de ejecución
    en el mismo período (``RutaTrabajo.fecha``).

    Une por ``orden_trabajo_id`` para no contar dos veces la misma OT
    (carga manual + Completar trabajo) dentro del rango.
    """
    ri = aliased(RutaItem)
    ir = aliased(IniciadorRuta)
    rt = aliased(RutaTrabajo)
    act_cierre = aliased(Actuaciones)
    return exists().where(
        ri.deleted_at.is_(None),
        ir.deleted_at.is_(None),
        ri.iniciador_ruta_id == ir.id,
        ri.ruta_trabajo_id == rt.id,
        ri.actuacion_id == act_cierre.id,
        act_cierre.orden_trabajo_id == Actuaciones.orden_trabajo_id,
        Actuaciones.orden_trabajo_id.isnot(None),
        ri.actuacion_id.isnot(None),
        ri.estado_ruta_item == "FINALIZADO",
        ri.estado_ejecucion.in_(estados_ejecucion),
        rt.estado_ruta == "PUBLICADA",
        rt.fecha >= desde,
        rt.fecha <= hasta,
    )


def _sin_ruta_item_propia_exists():
    """No hay RutaItem que apunte a esta actuación (carga documental suelta)."""
    return ~exists().where(
        RutaItem.actuacion_id == Actuaciones.id,
        RutaItem.deleted_at.is_(None),
    )


def _apply_manual_inspector_distrito(
    q,
    *,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
):
    """Filtros de distrito (domicilio de la actuación) e inspector (N:N)."""
    if distrito_id is not None:
        q = q.filter(
            exists().where(
                Domicilio.id == Actuaciones.domicilio_id,
                Domicilio.distrito_id == distrito_id,
                Domicilio.deleted_at.is_(None),
            )
        )
    if inspector_id is not None:
        q = q.filter(
            exists().where(
                actuaciones_inspector.c.actuaciones_id == Actuaciones.id,
                actuaciones_inspector.c.inspector_id == inspector_id,
                actuaciones_inspector.c.deleted_at.is_(None),
            )
        )
    return q


def _base_manual_query(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    *,
    exclusiva_ot: bool,
):
    """
    Actuaciones en rango de ``Actuaciones.fecha`` sin RutaItem propio.

    Si ``exclusiva_ot`` es True, excluye OTs que ya tienen cierre de ruta
    REALIZADO o NO_REALIZADO publicado.
    """
    q = db.session.query(Actuaciones).filter(
        Actuaciones.fecha >= desde,
        Actuaciones.fecha <= hasta,
        _sin_ruta_item_propia_exists(),
    )
    if exclusiva_ot:
        q = q.filter(
            ~_cierre_ruta_por_ot_exists(
                estados_ejecucion=("REALIZADO", "NO_REALIZADO"),
                desde=desde,
                hasta=hasta,
            )
        )
    return _apply_manual_inspector_distrito(
        q, distrito_id=distrito_id, inspector_id=inspector_id
    )


def _manual_realizada_clause():
    """Sin contraproducencia efectiva: vacío o NO_HUBO (cuenta como realizada)."""
    cp_key = func.upper(
        func.replace(
            func.replace(func.trim(Actuaciones.contraproducencia), "_", " "), "/", " "
        )
    )
    return or_(
        Actuaciones.contraproducencia.is_(None),
        func.trim(Actuaciones.contraproducencia) == "",
        cp_key == "NO HUBO",
    )


def count_actuaciones_manuales_realizadas(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> int:
    """Cuenta cargas manuales realizadas (sin cierre de ruta en la misma OT)."""
    q = _base_manual_query(
        desde, hasta, distrito_id, inspector_id, exclusiva_ot=True
    ).filter(_manual_realizada_clause())
    return int(q.with_entities(func.count(func.distinct(Actuaciones.id))).scalar() or 0)


def actuacion_ids_manuales_realizadas_subquery(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
):
    """Subquery de ``actuaciones.id`` manuales realizadas (para actas / riesgo)."""
    q = (
        _base_manual_query(desde, hasta, distrito_id, inspector_id, exclusiva_ot=True)
        .with_entities(Actuaciones.id)
        .filter(_manual_realizada_clause())
    )
    return q.distinct().subquery("act_manuales_realizadas")


def union_ids_realizadas_con_manuales(sq_ruta, sq_manual, *, name: str = "act_realizadas_union"):
    """
    UNION de IDs de cierres de ruta y cargas manuales.

    Expone columna ``id`` para joins de actas / decomiso.
    """
    col_ruta = list(sq_ruta.c)[0].label("id")
    col_manual = list(sq_manual.c)[0].label("id")
    return union(select(col_ruta), select(col_manual)).subquery(name)


def fetch_manuales_realizadas_rows(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> list[tuple[int, date]]:
    """
    Filas (actuacion_id, fecha) de cargas manuales realizadas.

    Parámetros:
        desde, hasta, distrito_id, inspector_id: mismos filtros del tablero.

    Retorno:
        Lista de pares id / fecha de actuación.
    """
    q = (
        _base_manual_query(desde, hasta, distrito_id, inspector_id, exclusiva_ot=True)
        .with_entities(Actuaciones.id, Actuaciones.fecha)
        .filter(_manual_realizada_clause())
    )
    return [(int(aid), fecha) for aid, fecha in q.all()]


def fetch_manuales_no_realizadas_rows(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> list[tuple[int, str | None, date, int | None]]:
    """
    Cargas manuales no realizadas: (id, contraproducencia, fecha, distrito_id).

    Parámetros:
        desde, hasta, distrito_id, inspector_id: filtros del tablero.

    Retorno:
        Lista de tuplas para fusionar con visitas de ruta.
    """
    q = (
        _base_manual_query(desde, hasta, distrito_id, inspector_id, exclusiva_ot=True)
        .outerjoin(Domicilio, Domicilio.id == Actuaciones.domicilio_id)
        .with_entities(
            Actuaciones.id,
            Actuaciones.contraproducencia,
            Actuaciones.fecha,
            Domicilio.distrito_id,
        )
        .filter(_has_contraproducencia_expr())
    )
    out: list[tuple[int, str | None, date, int | None]] = []
    for aid, contra, fecha, dist_id in q.all():
        if is_contraproducencia_excluida_valor(contra):
            continue
        out.append(
            (
                int(aid),
                None if contra is None else str(contra),
                fecha,
                int(dist_id) if dist_id is not None else None,
            )
        )
    return out
