"""
Agregaciones para GET /api/indicadores/no-realizadas.

Criterio de no realizada (cierre operativo):
- ``RutaItem`` en ruta ``PUBLICADA``, ``estado_ruta_item == NO_REALIZADO``,
  ``estado_ejecucion == NO_REALIZADO``, con ``actuacion_id`` no nulo.
- Fecha de cierre: ``coalesce(date(ejecutado_at), RutaTrabajo.fecha)`` en rango.
- La actuación vinculada tiene contraproducencia real (no vacía, no ``NO_HUBO``).

No incluye pendientes abiertos ni visitas ``REALIZADO`` sin contraproducencia.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from sqlalchemy import String, and_, func

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    _loose_key,
)
from app.domains.indicadores.schemas.no_realizadas_out import NoRealizadasPorTipo
from app.domains.indicadores.services.indicadores_resumen_service import (
    _CONTRAP_EXCLUIDAS_TOP,
    _has_contraproducencia_expr,
    _realizados_inspector_coincide,
)
from app.models import (
    Actuaciones,
    Distrito,
    Domicilio,
    IniciadorRuta,
    RutaItem,
    RutaTrabajo,
    actuaciones_inspector,
)

_TOP_CONTRAPRODUCCIONES_LIMIT = 10
_TOP_DISTRITOS_LIMIT = 10
_SIN_DISTRITO_ID = 0
_SIN_DISTRITO_CODIGO = "SIN_DISTRITO"
_SIN_DISTRITO_NOMBRE = "Sin distrito"

_TIPO_INICIADOR_A_BUCKET: dict[str, str] = {
    "RELEVAMIENTO": "inspeccion",
    "REINSPECCION_OFICIO": "reinspeccion_oficio",
    "REINSPECCION_NOTIFICACION": "reinspeccion_notificacion",
    "DENUNCIA": "denuncia",
}


def is_contraproducencia_excluida_valor(raw: str | None) -> bool:
    """True si el valor es vacío o equivalente a NO_HUBO (no cuenta como no realizada)."""
    if raw is None:
        return True
    s = str(raw).strip()
    if not s:
        return True
    return _loose_key(s) in _CONTRAP_EXCLUIDAS_TOP


def format_contraproducencia_label(raw: str) -> str:
    """
    Etiqueta legible para UI (español, sin camelCase ni enums crudos).

    Ej.: ``LOCAL_CERRADO`` → ``Local cerrado``; ``NO SE ENCUENTRA`` → ``No se encuentra``.
    """
    s = str(raw).strip()
    if not s:
        return s
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    words = _loose_key(s).split()
    if not words:
        return s
    return " ".join([words[0].capitalize(), *[w.lower() for w in words[1:]]])


def _contraproducencia_real_expr():
    """Contraproducencia persistida que cuenta como visita no realizada."""
    has_contra = _has_contraproducencia_expr()
    cp_key = func.upper(
        func.replace(func.replace(func.trim(Actuaciones.contraproducencia), "_", " "), "/", " ")
    )
    return and_(
        has_contra,
        cp_key != "NO HUBO",
        cp_key != "NO_HUBO",
    )


def _fecha_cierre_ruta_expr():
    return func.coalesce(func.date(RutaItem.ejecutado_at), RutaTrabajo.fecha)


def _no_realizadas_base_query(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
):
    """
    Query base de ítems de ruta no realizados (cierre en rango) con joins estándar.

    Retorno:
        Query SQLAlchemy (sin ejecutar) sobre ``RutaItem``.
    """
    q = (
        db.session.query(RutaItem.id)
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .outerjoin(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            IniciadorRuta.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.estado_ruta_item == "NO_REALIZADO",
            RutaItem.estado_ejecucion == "NO_REALIZADO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
            _contraproducencia_real_expr(),
            _fecha_cierre_ruta_expr() >= desde,
            _fecha_cierre_ruta_expr() <= hasta,
            IniciadorRuta.tipo_iniciador.in_(tuple(_TIPO_INICIADOR_A_BUCKET.keys())),
        )
    )
    if distrito_id is not None:
        q = q.filter(Domicilio.distrito_id == distrito_id)
    if inspector_id is not None:
        q = q.filter(_realizados_inspector_coincide(inspector_id))
    return q


def _no_realizadas_actuacion_ids_subquery(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
):
    """Subquery de ``actuaciones.id`` vinculadas a cierres no realizados en rango."""
    q = (
        db.session.query(Actuaciones.id)
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .outerjoin(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            IniciadorRuta.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.estado_ruta_item == "NO_REALIZADO",
            RutaItem.estado_ejecucion == "NO_REALIZADO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
            _contraproducencia_real_expr(),
            _fecha_cierre_ruta_expr() >= desde,
            _fecha_cierre_ruta_expr() <= hasta,
        )
    )
    if distrito_id is not None:
        q = q.filter(Domicilio.distrito_id == distrito_id)
    if inspector_id is not None:
        q = q.filter(_realizados_inspector_coincide(inspector_id))
    return q.distinct().subquery("act_no_realizadas")


def query_no_realizadas_por_tipo(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> NoRealizadasPorTipo:
    """
    Cuenta cierres no realizados por bucket de ``tipo_iniciador`` (4 tipos pedidos).
    """
    rows = (
        _no_realizadas_base_query(desde, hasta, distrito_id, inspector_id)
        .with_entities(
            IniciadorRuta.tipo_iniciador,
            func.count(func.distinct(RutaItem.id)),
        )
        .group_by(IniciadorRuta.tipo_iniciador)
        .all()
    )
    buckets = {b: 0 for b in _TIPO_INICIADOR_A_BUCKET.values()}
    for tipo, cnt in rows:
        bucket = _TIPO_INICIADOR_A_BUCKET.get(str(tipo))
        if bucket:
            buckets[bucket] += int(cnt)
    return NoRealizadasPorTipo(
        inspeccion=buckets["inspeccion"],
        reinspeccion_oficio=buckets["reinspeccion_oficio"],
        reinspeccion_notificacion=buckets["reinspeccion_notificacion"],
        denuncia=buckets["denuncia"],
    )


def query_top_contraproducencias_no_realizadas(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    *,
    limit: int = _TOP_CONTRAPRODUCCIONES_LIMIT,
) -> list[tuple[str, int]]:
    """
    Top contraproducencias solo entre actuaciones con cierre no realizado en rango.

    Excluye NO_HUBO; etiquetas normalizadas con ``format_contraproducencia_label``.
    """
    sq = _no_realizadas_actuacion_ids_subquery(
        desde, hasta, distrito_id, inspector_id
    )
    rows = (
        db.session.query(Actuaciones.contraproducencia, func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(_contraproducencia_real_expr())
        .group_by(Actuaciones.contraproducencia)
        .order_by(func.count(Actuaciones.id).desc())
        .all()
    )
    merged: dict[str, int] = {}
    for valor, cnt in rows:
        if is_contraproducencia_excluida_valor(valor):
            continue
        label = format_contraproducencia_label(str(valor))
        if not label:
            continue
        merged[label] = merged.get(label, 0) + int(cnt)
    ranked = sorted(merged.items(), key=lambda item: item[1], reverse=True)
    return ranked[:limit]


def query_distritos_con_mas_no_realizadas(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    *,
    limit: int = _TOP_DISTRITOS_LIMIT,
) -> list[tuple[int, str, str, int]]:
    """
    Agrupa cierres no realizados por distrito del domicilio.

    Retorno:
        Lista de (distrito_id, codigo, nombre, cantidad). Sin distrito → id 0, SIN_DISTRITO.
    """
    distrito_id_expr = func.coalesce(Domicilio.distrito_id, _SIN_DISTRITO_ID)
    distrito_codigo_expr = func.coalesce(
        func.cast(Distrito.codigo, String),
        _SIN_DISTRITO_CODIGO,
    )
    distrito_nombre_expr = func.coalesce(Distrito.nombre, _SIN_DISTRITO_NOMBRE)

    rows = (
        _no_realizadas_base_query(desde, hasta, distrito_id, inspector_id)
        .with_entities(
            distrito_id_expr,
            distrito_codigo_expr,
            distrito_nombre_expr,
            func.count(func.distinct(RutaItem.id)),
        )
        .outerjoin(Distrito, Distrito.id == Domicilio.distrito_id)
        .group_by(distrito_id_expr, distrito_codigo_expr, distrito_nombre_expr)
        .order_by(func.count(func.distinct(RutaItem.id)).desc())
        .limit(limit)
        .all()
    )
    out: list[tuple[int, str, str, int]] = []
    for did, codigo, nombre, cnt in rows:
        out.append(
            (
                int(did) if did is not None else _SIN_DISTRITO_ID,
                str(codigo) if codigo is not None else _SIN_DISTRITO_CODIGO,
                str(nombre) if nombre is not None else _SIN_DISTRITO_NOMBRE,
                int(cnt),
            )
        )
    return out
