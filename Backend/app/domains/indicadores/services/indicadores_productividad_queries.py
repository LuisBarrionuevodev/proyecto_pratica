"""
Agregaciones para GET /api/indicadores/productividad (por inspector).

Realizadas: misma base que ejecutivo (ruta del período + FINALIZADO + REALIZADO).
No realizadas: mismas no realizadas con contraproducencia que ``/no-realizadas``.
Actas: actuaciones de rutas del período con cierre REALIZADO + reglas de actas labradas.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy import and_, exists, func

from app.database import db
from app.domains.indicadores.schemas.productividad_out import (
    InspectorActasItem,
    InspectorNoRealizadasItem,
    InspectorRealizadasItem,
)
from app.domains.indicadores.services.indicadores_no_realizadas_queries import (
    _intentos_no_realizados_con_contraproducencia_filters,
    format_contraproducencia_label,
    is_contraproducencia_excluida_valor,
)
from app.domains.indicadores.services.indicadores_operativos_queries import (
    _fecha_periodo_operativo_expr,
    actuacion_ids_realizadas_subquery,
)
from app.domains.indicadores.services.indicadores_resumen_service import (
    _comprobacion_labarda_filter,
    _notificacion_labarda_exists,
    _realizados_inspector_coincide,
)
from app.models import (
    Actuaciones,
    Clausura,
    Decomiso,
    Domicilio,
    IniciadorRuta,
    Inspector,
    RutaItem,
    RutaTrabajo,
    actuaciones_inspector,
)

_TIPOS_PRODUCTIVIDAD = (
    "RELEVAMIENTO",
    "REINSPECCION_OFICIO",
    "REINSPECCION_NOTIFICACION",
    "DENUNCIA",
)

TIPO_INICIADOR_TO_PRODUCTIVIDAD_BUCKET: dict[str, str] = {
    "RELEVAMIENTO": "inspecciones",
    "REINSPECCION_OFICIO": "reinspecciones_oficio",
    "REINSPECCION_NOTIFICACION": "reinspecciones_notificacion",
    "DENUNCIA": "denuncias",
}

_BUCKET_LABELS: dict[str, str] = {
    "inspecciones": "Inspección",
    "reinspecciones_oficio": "Reinspección oficio",
    "reinspecciones_notificacion": "Reinspección notificación",
    "denuncias": "Denuncia",
}

_BUCKET_TIE_PRIORITY = (
    "inspecciones",
    "reinspecciones_oficio",
    "reinspecciones_notificacion",
    "denuncias",
)

_SIN_DATOS = "Sin datos"


def principal_bucket_label(counts: dict[str, int]) -> str:
    """
    Etiqueta del bucket con mayor cantidad; en empate gana el de menor prioridad en lista fija.

    Parámetros:
        counts: mapa bucket → cantidad (solo claves de productividad).

    Retorno:
        Etiqueta en español o ``Sin datos`` si total 0.
    """
    if not counts or sum(counts.values()) <= 0:
        return _SIN_DATOS
    max_val = max(counts.values())
    for key in _BUCKET_TIE_PRIORITY:
        if counts.get(key, 0) == max_val:
            return _BUCKET_LABELS[key]
    return _SIN_DATOS


def _principal_contraproducencia_por_inspector(
    rows: list[tuple[int, str | None, int]],
) -> dict[int, str]:
    """
    Contraproducencia más frecuente por inspector (etiqueta legible).

    Parámetros:
        rows: (inspector_id, contraproducencia cruda, cantidad).

    Retorno:
        Mapa inspector_id → etiqueta principal o ``Sin datos``.
    """
    merged: dict[int, dict[str, int]] = defaultdict(dict)
    for iid, raw, cnt in rows:
        if is_contraproducencia_excluida_valor(raw):
            continue
        label = format_contraproducencia_label(str(raw))
        if not label:
            continue
        merged[iid][label] = merged[iid].get(label, 0) + int(cnt)
    out: dict[int, str] = {}
    for iid, labels in merged.items():
        if not labels:
            out[iid] = _SIN_DATOS
            continue
        best = max(labels.items(), key=lambda x: x[1])
        out[iid] = best[0]
    return out


def _apply_distrito_filter(q, distrito_id: Optional[int]):
    if distrito_id is not None:
        q = q.join(Domicilio, Actuaciones.domicilio_id == Domicilio.id).filter(
            Domicilio.distrito_id == distrito_id,
            Domicilio.deleted_at.is_(None),
        )
    return q


def _realizadas_visita_subquery(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
):
    """
    Subquery de visitas realizadas (4 tipos de productividad) con actuación vinculada.

    Columnas: ``ruta_item_id``, ``actuacion_id``, ``tipo_iniciador``.
    """
    fecha_periodo = _fecha_periodo_operativo_expr()
    q = (
        db.session.query(
            RutaItem.id.label("ruta_item_id"),
            Actuaciones.id.label("actuacion_id"),
            IniciadorRuta.tipo_iniciador.label("tipo_iniciador"),
        )
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            IniciadorRuta.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
            IniciadorRuta.tipo_iniciador.in_(_TIPOS_PRODUCTIVIDAD),
            fecha_periodo >= desde,
            fecha_periodo <= hasta,
        )
    )
    q = _apply_distrito_filter(q, distrito_id)
    if inspector_id is not None:
        q = q.filter(_realizados_inspector_coincide(inspector_id))
    return q.subquery("vis_realizadas_prod")


def _no_realizadas_visita_subquery(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
):
    """Subquery de no realizadas con contraproducencia (misma base que ``/no-realizadas``)."""
    q = (
        db.session.query(
            RutaItem.id.label("ruta_item_id"),
            Actuaciones.id.label("actuacion_id"),
            IniciadorRuta.tipo_iniciador.label("tipo_iniciador"),
            Actuaciones.contraproducencia.label("contraproducencia"),
        )
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .filter(*_intentos_no_realizados_con_contraproducencia_filters(desde, hasta))
    )
    q = _apply_distrito_filter(q, distrito_id)
    if inspector_id is not None:
        q = q.filter(_realizados_inspector_coincide(inspector_id))
    return q.subquery("vis_no_realizadas_prod")


def _aggregate_por_inspector_y_tipo(
    visita_sq,
    *,
    inspector_id_filter: Optional[int] = None,
) -> dict[int, dict[str, object]]:
    """
    Agrupa visitas por inspector y tipo_iniciador (participación vía actuaciones_inspector).

    Retorno:
        inspector_id → {nombre, buckets: {bucket: count}}.
    """
    q = (
        db.session.query(
            Inspector.id,
            Inspector.nombre,
            visita_sq.c.tipo_iniciador,
            func.count(func.distinct(visita_sq.c.ruta_item_id)),
        )
        .select_from(visita_sq)
        .join(
            actuaciones_inspector,
            actuaciones_inspector.c.actuaciones_id == visita_sq.c.actuacion_id,
        )
        .join(Inspector, Inspector.id == actuaciones_inspector.c.inspector_id)
        .filter(actuaciones_inspector.c.deleted_at.is_(None))
        .group_by(Inspector.id, Inspector.nombre, visita_sq.c.tipo_iniciador)
    )
    if inspector_id_filter is not None:
        q = q.filter(Inspector.id == inspector_id_filter)

    acc: dict[int, dict[str, object]] = {}
    for iid, nombre, tipo, cnt in q.all():
        iid = int(iid)
        if iid not in acc:
            acc[iid] = {
                "nombre": str(nombre),
                "buckets": {b: 0 for b in TIPO_INICIADOR_TO_PRODUCTIVIDAD_BUCKET.values()},
            }
        bucket = TIPO_INICIADOR_TO_PRODUCTIVIDAD_BUCKET.get(str(tipo))
        if bucket:
            buckets = acc[iid]["buckets"]
            assert isinstance(buckets, dict)
            buckets[bucket] = int(buckets.get(bucket, 0)) + int(cnt)
    return acc


def query_inspectores_realizadas(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> list[InspectorRealizadasItem]:
    """
    Inspectores con visitas realizadas en rango (solo 4 tipos de productividad).

    ``total_realizadas`` = suma de los cuatro buckets (no incluye otros tipos de iniciador).
    """
    sq = _realizadas_visita_subquery(desde, hasta, distrito_id, inspector_id)
    acc = _aggregate_por_inspector_y_tipo(sq, inspector_id_filter=inspector_id)
    items: list[InspectorRealizadasItem] = []
    for iid, row in acc.items():
        buckets = row["buckets"]
        assert isinstance(buckets, dict)
        total = sum(int(buckets.get(b, 0)) for b in TIPO_INICIADOR_TO_PRODUCTIVIDAD_BUCKET.values())
        items.append(
            InspectorRealizadasItem(
                inspector_id=iid,
                inspector=str(row["nombre"]),
                total_realizadas=total,
                inspecciones=int(buckets.get("inspecciones", 0)),
                reinspecciones_oficio=int(buckets.get("reinspecciones_oficio", 0)),
                reinspecciones_notificacion=int(buckets.get("reinspecciones_notificacion", 0)),
                denuncias=int(buckets.get("denuncias", 0)),
                tipo_principal=principal_bucket_label(buckets),
            )
        )
    items.sort(key=lambda x: x.total_realizadas, reverse=True)
    return items


def query_inspectores_no_realizadas(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> list[InspectorNoRealizadasItem]:
    """Inspectores con visitas no realizadas en rango y contraproducencia principal."""
    sq = _no_realizadas_visita_subquery(desde, hasta, distrito_id, inspector_id)
    acc = _aggregate_por_inspector_y_tipo(sq, inspector_id_filter=inspector_id)

    cp_rows = (
        db.session.query(
            Inspector.id,
            sq.c.contraproducencia,
            func.count(func.distinct(sq.c.ruta_item_id)),
        )
        .select_from(sq)
        .join(
            actuaciones_inspector,
            actuaciones_inspector.c.actuaciones_id == sq.c.actuacion_id,
        )
        .join(Inspector, Inspector.id == actuaciones_inspector.c.inspector_id)
        .filter(actuaciones_inspector.c.deleted_at.is_(None))
        .group_by(Inspector.id, sq.c.contraproducencia)
    )
    if inspector_id is not None:
        cp_rows = cp_rows.filter(Inspector.id == inspector_id)
    cp_principal = _principal_contraproducencia_por_inspector(
        [(int(i), raw, int(c)) for i, raw, c in cp_rows.all()]
    )

    items: list[InspectorNoRealizadasItem] = []
    for iid, row in acc.items():
        buckets = row["buckets"]
        assert isinstance(buckets, dict)
        total = sum(int(buckets.get(b, 0)) for b in TIPO_INICIADOR_TO_PRODUCTIVIDAD_BUCKET.values())
        items.append(
            InspectorNoRealizadasItem(
                inspector_id=iid,
                inspector=str(row["nombre"]),
                total_no_realizadas=total,
                contraproducencia_principal=cp_principal.get(iid, _SIN_DATOS),
                inspecciones=int(buckets.get("inspecciones", 0)),
                reinspecciones_oficio=int(buckets.get("reinspecciones_oficio", 0)),
                reinspecciones_notificacion=int(buckets.get("reinspecciones_notificacion", 0)),
                denuncias=int(buckets.get("denuncias", 0)),
            )
        )
    items.sort(key=lambda x: x.total_no_realizadas, reverse=True)
    return items


def _actas_count_por_inspector(
    sq,
    acta_filter,
    inspector_id: Optional[int] = None,
) -> dict[int, tuple[str, int]]:
    """Cuenta actuaciones distintas con acta labrada por inspector participante."""
    q = (
        db.session.query(
            Inspector.id,
            Inspector.nombre,
            func.count(func.distinct(Actuaciones.id)),
        )
        .select_from(Actuaciones)
        .join(sq, sq.c.id == Actuaciones.id)
        .join(
            actuaciones_inspector,
            actuaciones_inspector.c.actuaciones_id == Actuaciones.id,
        )
        .join(Inspector, Inspector.id == actuaciones_inspector.c.inspector_id)
        .filter(actuaciones_inspector.c.deleted_at.is_(None), acta_filter)
        .group_by(Inspector.id, Inspector.nombre)
    )
    if inspector_id is not None:
        q = q.filter(Inspector.id == inspector_id)
    return {int(iid): (str(nombre), int(cnt)) for iid, nombre, cnt in q.all()}


def query_actas_por_inspector(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> list[InspectorActasItem]:
    """
    Actas labradas por inspector (participación: cada inspector de la actuación suma la acta).

    Solo actuaciones de rutas del período con cierre REALIZADO (misma base que ejecutivo/riesgo).
    """
    sq = actuacion_ids_realizadas_subquery(desde, hasta, distrito_id, inspector_id)

    notif = _actas_count_por_inspector(
        sq,
        and_(
            Actuaciones.notificacion_id.isnot(None),
            _notificacion_labarda_exists(),
        ),
        inspector_id,
    )
    comp = _actas_count_por_inspector(sq, _comprobacion_labarda_filter(), inspector_id)
    clau = _actas_count_por_inspector(
        sq,
        exists().where(Clausura.actuacion_id == Actuaciones.id),
        inspector_id,
    )
    deco = _actas_count_por_inspector(
        sq,
        exists().where(Decomiso.actuacion_id == Actuaciones.id),
        inspector_id,
    )

    all_ids = set(notif) | set(comp) | set(clau) | set(deco)
    items: list[InspectorActasItem] = []
    for iid in all_ids:
        nombre = (
            notif.get(iid, (None, 0))[0]
            or comp.get(iid, (None, 0))[0]
            or clau.get(iid, (None, 0))[0]
            or deco.get(iid, (None, 0))[0]
            or ""
        )
        n = notif.get(iid, ("", 0))[1]
        c = comp.get(iid, ("", 0))[1]
        cl = clau.get(iid, ("", 0))[1]
        d = deco.get(iid, ("", 0))[1]
        total = n + c + cl + d
        items.append(
            InspectorActasItem(
                inspector_id=iid,
                inspector=nombre,
                notificacion=n,
                comprobacion=c,
                clausura=cl,
                decomiso=d,
                total_actas=total,
            )
        )
    items.sort(key=lambda x: x.total_actas, reverse=True)
    return items
