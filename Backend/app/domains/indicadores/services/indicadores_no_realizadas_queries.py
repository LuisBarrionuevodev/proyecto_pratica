"""
Agregaciones para GET /api/indicadores/no-realizadas.

KPI Dashboard — no realizada con contraproducencia (trabajo no concretado):
- ``RutaItem`` en ruta ``PUBLICADA``, cierre no realizado (``FINALIZADO``+``NO_REALIZADO``
  canónico de Completar trabajo, o legado ``NO_REALIZADO``+``NO_REALIZADO``), con
  ``actuacion_id`` no nulo.
- Período: ``RutaTrabajo.fecha`` en rango (día operativo de la ruta).
- Contraproducencia real en la actuación (no vacía, no ``NO_HUBO``).
- ``tipo_iniciador`` dentro de los buckets del bloque (incluye circuito oficio híbrido).

No exige cierre administrativo terminal del iniciador (``LOCAL CERRADO`` reencolable cuenta).
Para cierres finales sin reencola, ver ``_no_realizadas_finales_administrativas_filters()``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import String, and_, func, or_

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    _loose_key,
)
from app.domains.indicadores.schemas.no_realizadas_out import NoRealizadasPorTipo
from app.domains.indicadores.services.indicadores_operativos_queries import (
    TIPOS_INICIADOR_OFICIO_REALIZADA,
    _fecha_periodo_operativo_expr,
)
from app.domains.indicadores.services.indicadores_resumen_service import (
    _CONTRAP_EXCLUIDAS_TOP,
    _has_contraproducencia_expr,
    _realizados_inspector_coincide,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
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
    "RATIFICACION_CLAUSURA_OFICIO": "reinspeccion_oficio",
    "RATIFICACION_DECOMISO_OFICIO": "reinspeccion_oficio",
    "VERIFICAR_INFORMAR_OFICIO": "reinspeccion_oficio",
    "REINSPECCION_NOTIFICACION": "reinspeccion_notificacion",
    "DENUNCIA": "denuncia",
}

_TIPOS_NO_REALIZADAS = (
    "RELEVAMIENTO",
    "REINSPECCION_NOTIFICACION",
    "DENUNCIA",
) + TIPOS_INICIADOR_OFICIO_REALIZADA


@dataclass(frozen=True)
class NoRealizadaVisitaRow:
    """
    Visita no realizada única (un ``ruta_item_id``) dentro del universo de indicadores.

    Base compartida entre ``/no-realizadas`` y ``/productividad``.
    """

    ruta_item_id: int
    actuacion_id: int
    contraproducencia: str | None
    distrito_id: int | None
    fecha: date


def fetch_no_realizadas_visita_rows(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> list[NoRealizadaVisitaRow]:
    """
    Lista de visitas no realizadas con contraproducencia real (una fila por ``ruta_item_id``).

    Parámetros:
        desde, hasta: rango sobre ``RutaTrabajo.fecha``.
        distrito_id, inspector_id: filtros opcionales.

    Retorno:
        Filas únicas por ``ruta_item_id`` con actuación y contraproducencia persistida.
    """
    fecha_periodo = _fecha_periodo_operativo_expr()
    q = (
        db.session.query(
            RutaItem.id,
            RutaItem.actuacion_id,
            Actuaciones.contraproducencia,
            Domicilio.distrito_id,
            fecha_periodo,
        )
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .outerjoin(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .filter(*_intentos_no_realizados_con_contraproducencia_filters(desde, hasta))
        .order_by(RutaItem.id)
    )
    if distrito_id is not None:
        q = q.filter(Domicilio.distrito_id == distrito_id)
    if inspector_id is not None:
        q = q.filter(_realizados_inspector_coincide(inspector_id))

    seen: set[int] = set()
    out: list[NoRealizadaVisitaRow] = []
    for ri_id, act_id, contra, dist_id, fecha in q.all():
        ri_id = int(ri_id)
        if ri_id in seen:
            continue
        seen.add(ri_id)
        out.append(
            NoRealizadaVisitaRow(
                ruta_item_id=ri_id,
                actuacion_id=int(act_id),
                contraproducencia=contra if contra is None else str(contra),
                distrito_id=int(dist_id) if dist_id is not None else None,
                fecha=fecha,
            )
        )
    return out


def aggregate_contraproducencia_buckets_from_visita_rows(
    rows: list[NoRealizadaVisitaRow],
) -> dict[str, int]:
    """
    Agrupa visitas únicas en buckets fijos de contraproducencia.

    Retorno:
        Mapa bucket → cantidad (una visita = un conteo máximo por bucket).
    """
    from app.domains.indicadores.utils.contraproducencia_indicador_buckets import (
        empty_contraproducencia_buckets,
        merge_contraproducencia_counts,
    )

    buckets = empty_contraproducencia_buckets()
    for row in rows:
        merge_contraproducencia_counts(buckets, row.contraproducencia, 1)
    return buckets


def estados_iniciador_terminal_no_realizada() -> tuple[str, ...]:
    """
    Estados de iniciador que indican cierre administrativo (sin reencola).

    Alineado a ``inactive_estados()`` del dominio de rutas:
    ``ANULADO``, ``CERRADO``, ``CERRADO_NO_EXISTE_LOCAL``.
    """
    return inactive_estados()


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


def _ruta_item_cerrado_no_realizado_expr():
    """
    Ítem cerrado como visita no realizada (Completar trabajo).

    Par canónico: ``FINALIZADO`` + ``NO_REALIZADO``.
    Legado: ``estado_ruta_item`` y ``estado_ejecucion`` en ``NO_REALIZADO``.
    Excluye ítems ``EN_PROCESO`` sin cierre.
    """
    return or_(
        and_(
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "NO_REALIZADO",
        ),
        and_(
            RutaItem.estado_ruta_item == "NO_REALIZADO",
            RutaItem.estado_ejecucion == "NO_REALIZADO",
        ),
    )


def _intentos_no_realizados_con_contraproducencia_filters(
    desde: date,
    hasta: date,
    *,
    limitar_tipos_dashboard: bool = True,
):
    """
    Filtros del KPI visible: trabajos NO_REALIZADO con contraproducencia real en el período.

    Período operativo: ``RutaTrabajo.fecha``. No filtra ``estado_iniciador``.
    """
    fecha_periodo = _fecha_periodo_operativo_expr()
    clauses = [
        RutaItem.deleted_at.is_(None),
        IniciadorRuta.deleted_at.is_(None),
        RutaItem.actuacion_id.isnot(None),
        _ruta_item_cerrado_no_realizado_expr(),
        RutaTrabajo.estado_ruta == "PUBLICADA",
        _contraproducencia_real_expr(),
        fecha_periodo >= desde,
        fecha_periodo <= hasta,
    ]
    if limitar_tipos_dashboard:
        clauses.append(IniciadorRuta.tipo_iniciador.in_(_TIPOS_NO_REALIZADAS))
    return clauses


# Alias legible para el endpoint y productividad.
_no_realizadas_operativo_filters = _intentos_no_realizados_con_contraproducencia_filters


def _no_realizadas_finales_administrativas_filters(
    desde: date,
    hasta: date,
    *,
    limitar_tipos_dashboard: bool = True,
):
    """
    Cierres NO_REALIZADO con contraproducencia y iniciador en estado terminal (sin reencola).

    Solo diagnóstico o bloques futuros; no alimenta ``/no-realizadas``.
    """
    return [
        *_intentos_no_realizados_con_contraproducencia_filters(
            desde, hasta, limitar_tipos_dashboard=limitar_tipos_dashboard
        ),
        IniciadorRuta.estado_iniciador.in_(estados_iniciador_terminal_no_realizada()),
    ]


# Alias retrocompatible (a6).
_no_realizadas_administrativas_filters = _no_realizadas_finales_administrativas_filters


def _no_realizadas_base_query(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
):
    """
    Query base de ítems no realizados con contraproducencia (KPI Dashboard).

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
        .filter(*_intentos_no_realizados_con_contraproducencia_filters(desde, hasta))
    )
    if distrito_id is not None:
        q = q.filter(Domicilio.distrito_id == distrito_id)
    if inspector_id is not None:
        q = q.filter(_realizados_inspector_coincide(inspector_id))
    return q


def _no_realizadas_administrativas_base_query(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
):
    """Query base de cierres finales administrativos (diagnóstico / uso futuro)."""
    q = (
        db.session.query(RutaItem.id)
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .outerjoin(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .filter(*_no_realizadas_finales_administrativas_filters(desde, hasta))
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
    """Subquery de actuaciones con cierre no realizado y contraproducencia en rango."""
    q = (
        db.session.query(Actuaciones.id)
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .outerjoin(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .filter(*_intentos_no_realizados_con_contraproducencia_filters(desde, hasta))
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
    Cuenta no realizadas con contraproducencia por bucket de ``tipo_iniciador``.
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
    Top contraproducencias entre no realizadas con contraproducencia en rango.

    Excluye NO_HUBO; etiquetas normalizadas con ``format_contraproducencia_label``.
    Cuenta visitas únicas (``ruta_item_id``), no actuaciones.
    """
    rows = fetch_no_realizadas_visita_rows(desde, hasta, distrito_id, inspector_id)
    merged: dict[str, int] = {}
    for row in rows:
        if is_contraproducencia_excluida_valor(row.contraproducencia):
            continue
        label = format_contraproducencia_label(str(row.contraproducencia))
        if not label:
            continue
        merged[label] = merged.get(label, 0) + 1
    ranked = sorted(merged.items(), key=lambda item: item[1], reverse=True)
    return ranked[:limit]


def query_contraproducencias_resumen_counts(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> tuple[int, dict[str, int]]:
    """
    Cuenta no realizadas agrupadas en buckets fijos de contraproducencia.

    Retorno:
        (total, mapa bucket → cantidad). Una visita (``ruta_item_id``) por bucket como máximo.
    """
    buckets = aggregate_contraproducencia_buckets_from_visita_rows(
        fetch_no_realizadas_visita_rows(desde, hasta, distrito_id, inspector_id)
    )
    total = sum(buckets.values())
    return total, buckets


def query_distritos_con_mas_no_realizadas(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    *,
    limit: int = _TOP_DISTRITOS_LIMIT,
) -> list[tuple[int, str, str, int]]:
    """
    Agrupa no realizadas con contraproducencia por distrito del domicilio.

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
