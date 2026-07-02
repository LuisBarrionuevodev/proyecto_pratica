from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import exists, func, or_, and_
from sqlalchemy.orm import joinedload

from app.database import db
from app.models import Actuaciones, Domicilio, Expediente, IniciadorRuta, Notificacion, RutaItem
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    list_reinspeccion_notificacion_operativas,
    materializacion_notificacion_vencida_on_read_enabled,
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.actuaciones.utils.actuaciones_bandeja_eager import (
    apply_bandeja_grid_eager,
    reload_actuaciones_bandeja_eager,
)
from app.domains.actuaciones.utils.notificacion_plazo_slice import (
    filter_actuaciones_notificacion_por_plazo_slice,
)


def _apply_fecha(query, desde, hasta):
    if desde:
        query = query.filter(Actuaciones.fecha >= desde)
    if hasta:
        query = query.filter(Actuaciones.fecha <= hasta)
    return query


def _apply_distrito_optional(query, distrito_id: Optional[int]):
    """Restringe por ``domicilio.distrito_id`` (join único)."""
    if distrito_id is None:
        return query
    return query.join(Domicilio, Actuaciones.domicilio_id == Domicilio.id).filter(
        Domicilio.distrito_id == int(distrito_id)
    )


def _domicilios_pendientes_query(filters: ActuacionesPendientesFilters):
    query = (
        Actuaciones.query.join(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .filter(Domicilio.deleted_at.is_(None))
        .filter(
            or_(
                Domicilio.calle_norm_status.is_(None),
                Domicilio.calle_norm_status != "OK",
                and_(
                    Domicilio.numero_tipo == "ESQUINA",
                    or_(
                        Domicilio.esquina_norm_status.is_(None),
                        Domicilio.esquina_norm_status != "OK",
                    ),
                ),
            )
        )
    )
    return _apply_fecha(query, filters.desde, filters.hasta)


def _sin_expediente_query(filters: ActuacionesPendientesFilters):
    """
    Comprobación sin **expediente de envío** aún: mismo criterio que ``pendientes-vinc-acta``
    (expediente ligado a la comprobación con ``oficio_id`` NULL y no borrado).
    No basta con «ningún expediente»: el de respuesta de oficio lleva ``oficio_id`` y no debe
    bloquear el alta de envío ni ocultar la fila de esta bandeja por error.
    """
    subq = exists().where(
        and_(
            Expediente.comprobacion_id == Actuaciones.comprobacion_id,
            Expediente.oficio_id.is_(None),
            Expediente.deleted_at.is_(None),
        )
    )
    query = (
        Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(~subq)
    )
    return _apply_fecha(query, filters.desde, filters.hasta)


def _sin_expediente_notificacion_query(filters: ActuacionesPendientesFilters):
    """
    Bandeja de gestión de expedientes de plazo por rama NOTIFICACION.

    Regla para este slice:
    - actuación con notificación (puede coexistir comprobación en la misma actuación; la gestión
      de plazo por notificación sigue siendo un canal paralelo a la de comprobación).

    Nota: puede haber 0..N expedientes `PRORROGA_NOTIFICACION` por notificación; la fila sigue
    apareciendo (gestión continua). Métricas `dias_restantes` / `plazos_otorgados` en presenter.
    """
    query = Actuaciones.query.filter(Actuaciones.notificacion_id.isnot(None))
    return _apply_fecha(query, filters.desde, filters.hasta)


def build_notificacion_expediente_bandeja_metrics(
    acts: List[Actuaciones],
) -> tuple[dict[int, int], dict[int, date | None], dict[int, int]]:
    """
    Para actuaciones con notificación en la bandeja: cuenta expedientes de plazo por
    `notificacion_id`, carga `fecha_vencimiento` y suma de días de prórroga desde `Notificacion`.

    Incluye actuaciones que también tienen comprobación en la misma fila (canal paralelo).
    """
    noti_ids = list(
        {
            int(a.notificacion_id)
            for a in acts
            if a.notificacion_id is not None
        }
    )
    if not noti_ids:
        return {}, {}, {}

    rows = (
        db.session.query(Expediente.notificacion_id, func.count(Expediente.id))
        .filter(Expediente.notificacion_id.in_(noti_ids))
        .filter(Expediente.tipo_expediente == "PRORROGA_NOTIFICACION")
        .filter(Expediente.deleted_at.is_(None))
        .group_by(Expediente.notificacion_id)
        .all()
    )
    plazos_map: dict[int, int] = {int(nid): int(c) for nid, c in rows}

    notis = Notificacion.query.filter(Notificacion.id.in_(noti_ids)).all()
    venc_map: dict[int, date | None] = {int(n.id): n.fecha_vencimiento for n in notis}
    prorroga_dias_map: dict[int, int] = {int(n.id): int(n.prorroga_dias or 0) for n in notis}

    return plazos_map, venc_map, prorroga_dias_map


def dedupe_actuaciones_canonicas_por_notificacion(acts: List[Actuaciones]) -> List[Actuaciones]:
    """
    Una fila por ``notificacion_id`` en historial/gestión: evita duplicar INSPECCION origen + REINSPECCION.

    Criterio: preferir actuación ``INSPECCION`` de mayor ``id``; si no hay, la de mayor ``id`` del grupo.
    """
    by_noti: Dict[int, List[Actuaciones]] = defaultdict(list)
    sin_noti: List[Actuaciones] = []
    for act in acts:
        if act.notificacion_id is None:
            sin_noti.append(act)
            continue
        by_noti[int(act.notificacion_id)].append(act)

    out: List[Actuaciones] = list(sin_noti)
    for group in by_noti.values():
        inspecciones = [a for a in group if getattr(a, "tipo", None) == "INSPECCION"]
        if inspecciones:
            out.append(max(inspecciones, key=lambda a: int(a.id)))
        else:
            out.append(max(group, key=lambda a: int(a.id)))
    out.sort(key=lambda a: int(a.id), reverse=True)
    return out


def build_reinspeccion_comprobacion_por_actuacion_id(acts: List[Actuaciones]) -> Dict[int, Optional[Actuaciones]]:
    """
    Comprobación de seguimiento en historial de notificación: la realizada en la actuación
    ``REINSPECCION`` vinculada a la misma ``notificacion_id`` (reinspección por notificación vencida).

    No usa comprobación de la actuación origen ni búsqueda genérica por domicilio.

    Args:
        acts: actuaciones devueltas por bandeja / historial de notificaciones.

    Returns:
        Mapa ``actuacion_id`` origen -> actuación REINSPECCION con comprobación, o ``None``.
    """
    out: Dict[int, Optional[Actuaciones]] = {int(a.id): None for a in acts}
    refs = [a for a in acts if getattr(a, "notificacion_id", None)]
    if not refs:
        return out

    noti_ids = {int(a.notificacion_id) for a in refs}

    rein_direct = (
        Actuaciones.query.filter(Actuaciones.notificacion_id.in_(noti_ids))
        .filter(Actuaciones.tipo == "REINSPECCION")
        .filter(Actuaciones.comprobacion_id.isnot(None))
        .options(joinedload(Actuaciones.inspector), joinedload(Actuaciones.comprobacion))
        .all()
    )
    by_noti: Dict[int, List[Actuaciones]] = defaultdict(list)
    for c in rein_direct:
        by_noti[int(c.notificacion_id)].append(c)

    rein_via_item: Dict[int, Actuaciones] = {}
    item_rows = (
        db.session.query(IniciadorRuta.notificacion_id, Actuaciones)
        .join(RutaItem, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(Actuaciones, Actuaciones.id == RutaItem.actuacion_id)
        .filter(IniciadorRuta.notificacion_id.in_(noti_ids))
        .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION")
        .filter(IniciadorRuta.deleted_at.is_(None))
        .filter(RutaItem.deleted_at.is_(None))
        .filter(Actuaciones.tipo == "REINSPECCION")
        .filter(Actuaciones.comprobacion_id.isnot(None))
        .options(joinedload(Actuaciones.inspector), joinedload(Actuaciones.comprobacion))
        .all()
    )
    for noti_id, act_rein in item_rows:
        if noti_id is None:
            continue
        nid = int(noti_id)
        prev = rein_via_item.get(nid)
        key_new = (act_rein.fecha or date.min, int(act_rein.id))
        if prev is None or key_new > (prev.fecha or date.min, int(prev.id)):
            rein_via_item[nid] = act_rein

    for ref in refs:
        rid = int(ref.id)
        nid = int(ref.notificacion_id)  # type: ignore[arg-type]
        candidates: List[Actuaciones] = [c for c in by_noti.get(nid, []) if int(c.id) != rid]
        via = rein_via_item.get(nid)
        if via is not None and int(via.id) != rid:
            candidates.append(via)
        if not candidates:
            continue
        candidates.sort(key=lambda x: ((x.fecha or date.min), int(x.id)))
        out[rid] = candidates[-1]

    return out


def build_posterior_comprobacion_por_actuacion_id(acts: List[Actuaciones]) -> Dict[int, Optional[Actuaciones]]:
    """
    Por cada actuación NOTIFICACION-only con domicilio, busca la primera visita **posterior**
    (fecha, id) del mismo domicilio que ya tenga acta de comprobación.

    Sirve para enriquecer la bandeja de expediente de plazo: la fila es la actuación de
    notificación; la comprobación suele registrarse en otra actuación del mismo local.

    Args:
        acts: actuaciones devueltas por ``get_pendientes_expediente`` (u origen equivalente).

    Returns:
        Mapa ``actuacion_id`` -> actuación posterior o ``None``. Incluye entrada por cada
        ``acts[].id``; solo las referencias NOTIFICACION-only pueden apuntar a una posterior no nula.
    """
    out: Dict[int, Optional[Actuaciones]] = {int(a.id): None for a in acts}
    refs = [
        a
        for a in acts
        if getattr(a, "notificacion_id", None)
        and not getattr(a, "comprobacion_id", None)
        and getattr(a, "domicilio_id", None)
    ]
    if not refs:
        return out

    dom_ids = {int(a.domicilio_id) for a in refs if a.domicilio_id is not None}
    if not dom_ids:
        return out

    candidates = (
        Actuaciones.query.filter(Actuaciones.domicilio_id.in_(dom_ids))
        .filter(Actuaciones.comprobacion_id.isnot(None))
        .options(joinedload(Actuaciones.inspector), joinedload(Actuaciones.comprobacion))
        .all()
    )

    by_dom: Dict[int, List[Actuaciones]] = defaultdict(list)
    for c in candidates:
        by_dom[int(c.domicilio_id)].append(c)

    for lst in by_dom.values():
        lst.sort(key=lambda x: ((x.fecha or date.min), int(x.id)))

    for ref in refs:
        rid = int(ref.id)
        dom = int(ref.domicilio_id)  # type: ignore[arg-type]
        ref_key = (ref.fecha or date.min, rid)
        chosen: Optional[Actuaciones] = None
        for c in by_dom.get(dom, []):
            ck = (c.fecha or date.min, int(c.id))
            if ck <= ref_key:
                continue
            chosen = c
            break
        out[rid] = chosen

    return out


def _notificaciones_pendientes_query(filters: ActuacionesPendientesFilters):
    """
    Retorna query operativa para notificaciones vencidas con iniciador materializado.

    Fase C: la materialización corre por CLI / `flask sync-notificaciones-vencidas` / scheduler, no por este
    GET. Solo si `SYNC_NOTIFICACIONES_VENCIDAS_ON_READ=1` se invoca sync aquí (compatibilidad transitoria).

    Luego filtramos por rango de fecha de actuación para mantener contrato del endpoint.
    """
    if materializacion_notificacion_vencida_on_read_enabled():
        sync_iniciadores_reinspeccion_notificacion()
    act_ids = [a.id for a in list_reinspeccion_notificacion_operativas()]
    if not act_ids:
        return Actuaciones.query.filter(False)
    query = Actuaciones.query.filter(Actuaciones.id.in_(act_ids))
    return _apply_fecha(query, filters.desde, filters.hasta)


def get_pendientes_summary(filters: ActuacionesPendientesFilters) -> Dict[str, int]:
    """
    Obtiene conteos de pendientes de Actuaciones (domicilios, sin expediente, notificaciones).
    """
    domicilios = _domicilios_pendientes_query(filters).count()
    sin_expediente = _sin_expediente_query(filters).count()
    notificaciones = _notificaciones_pendientes_query(filters).count()
    total = domicilios + sin_expediente + notificaciones

    return {
        "total": total,
        "domicilios": domicilios,
        "sin_expediente": sin_expediente,
        "notificaciones": notificaciones,
    }


def get_pendientes_list(filters: ActuacionesPendientesFilters) -> List[Actuaciones]:
    """
    Lista actuaciones pendientes según tipo:
      - domicilios
      - sin_expediente
      - notificaciones
    """
    if filters.tipo == "domicilios":
        query = _domicilios_pendientes_query(filters)
    elif filters.tipo == "sin_expediente":
        query = _sin_expediente_query(filters)
    elif filters.tipo == "notificaciones":
        query = _notificaciones_pendientes_query(filters)
    else:
        return []

    return query.order_by(Actuaciones.id.desc()).all()


def get_pendientes_expediente(filters: ActuacionesPendientesFilters) -> List[Actuaciones]:
    """
    Lista actuaciones pendientes de expediente.

    Reutiliza y unifica la lógica administrativa para dos ramas:
    - COMPROBACION: actuación con comprobación sin expediente en su comprobación.
    - NOTIFICACION: actuación con notificación (puede incluir la misma actuación que ya tiene
      comprobación; el presenter marca el canal según ``source_type`` del filtro).

    source_type (filtro):
    - all
    - notificacion
    - comprobacion
    """
    source_type = (filters.source_type or "all").lower()
    distrito_id = getattr(filters, "distrito_id", None)

    if source_type == "comprobacion":
        query = apply_bandeja_grid_eager(
            _apply_distrito_optional(_sin_expediente_query(filters), distrito_id)
        )
    elif source_type == "notificacion":
        query = apply_bandeja_grid_eager(
            _apply_distrito_optional(_sin_expediente_notificacion_query(filters), distrito_id)
        )
    else:
        query_comp = _apply_distrito_optional(_sin_expediente_query(filters), distrito_id)
        query_noti = _apply_distrito_optional(_sin_expediente_notificacion_query(filters), distrito_id)
        query = query_comp.union(query_noti)

    if source_type in ("comprobacion", "notificacion"):
        acts: List[Actuaciones] = query.order_by(Actuaciones.id.desc()).all()
    else:
        acts = reload_actuaciones_bandeja_eager(query.order_by(Actuaciones.id.desc()).all())
    if source_type == "notificacion":
        acts = dedupe_actuaciones_canonicas_por_notificacion(acts)
    if source_type == "notificacion" and _notificacion_documental_filters_active(filters):
        acts = _filter_actuaciones_documental_notificacion(acts, filters)
    if source_type == "notificacion" and getattr(filters, "plazo_slice", None):
        acts = filter_actuaciones_notificacion_por_plazo_slice(acts, filters.plazo_slice)
    return acts


def _notificacion_documental_filters_active(filters: ActuacionesPendientesFilters) -> bool:
    """True si llegó algún filtro documental opcional (solo rama notificación)."""
    return bool(
        filters.contribuyente_q
        or filters.calle_q
        or filters.numero_notificacion
        or filters.motivo_q
    )


def _filter_actuaciones_documental_notificacion(
    acts: List[Actuaciones],
    filters: ActuacionesPendientesFilters,
) -> List[Actuaciones]:
    """
    Filtra en memoria actuaciones NOTIFICACION-only usando el mismo snapshot que la grilla
    (``actuacion_to_grid_row``), criterio subcadena case-insensitive como recorrido documental.
    """
    if not acts:
        return []
    counts_by_eo = build_counts_by_eo_from_actuaciones(acts)
    out: List[Actuaciones] = []
    for act in acts:
        row = actuacion_to_grid_row(act, counts_by_eo=counts_by_eo)
        if filters.contribuyente_q:
            blob = (
                f"{row.get('contrib_apellido') or ''} {row.get('contrib_nombre') or ''} "
                f"{row.get('razon_social') or ''}"
            ).lower()
            if filters.contribuyente_q.lower() not in blob:
                continue
        if filters.calle_q:
            calle = (row.get("calle") or "").lower()
            if filters.calle_q.lower() not in calle:
                continue
        if filters.numero_notificacion:
            num = (row.get("acta_notificacion_num") or "").replace(" ", "").lower()
            q = filters.numero_notificacion.replace(" ", "").lower()
            if q not in num:
                continue
        if filters.motivo_q:
            parts = [
                row.get("notificacion_motivo_1"),
                row.get("notificacion_motivo_2"),
                row.get("notificacion_motivo_3"),
            ]
            blob = " ".join([str(p) for p in parts if p]).lower()
            if filters.motivo_q.lower() not in blob:
                continue
        out.append(act)
    return out


def get_pendientes_oficio(filters: ActuacionesPendientesFilters) -> List[Actuaciones]:
    """
    Lista actuaciones en estado "esperando oficio".

    Reglas:
    - Debe pertenecer a rama COMPROBACION (`comprobacion_id` no nulo).
    - Debe existir expediente original de comprobación (ENVIO_ACTA u otro sin oficio).
    - No debe existir expediente de respuesta de oficio para esa comprobación.
    """
    has_expediente_original = exists().where(
        and_(
            Expediente.comprobacion_id == Actuaciones.comprobacion_id,
            Expediente.oficio_id.is_(None),
            Expediente.deleted_at.is_(None),
        )
    )
    has_respuesta_oficio = exists().where(
        and_(
            Expediente.comprobacion_id == Actuaciones.comprobacion_id,
            Expediente.oficio_id.isnot(None),
            or_(
                Expediente.tipo_expediente == "RESPUESTA_OFICIO",
                Expediente.tipo_expediente.is_(None),
            ),
            Expediente.deleted_at.is_(None),
        )
    )

    query = apply_bandeja_grid_eager(
        Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(has_expediente_original)
        .filter(~has_respuesta_oficio)
    )
    query = _apply_fecha(query, filters.desde, filters.hasta)
    query = _apply_distrito_optional(query, getattr(filters, "distrito_id", None))
    return query.order_by(Actuaciones.id.desc()).all()
