from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import and_, func, or_

from app.database import db
from app.models import (
    Actuaciones,
    Domicilio,
    DomicilioGeocode,
    Relevamiento,
    Rubro,
    Distrito,
    Inspector,
)
from app.models.actuaciones_inspector import actuaciones_inspector


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except Exception:
        return None


def _apply_date_filters(query, model, desde: Optional[date], hasta: Optional[date]):
    if desde:
        query = query.filter(model.fecha >= desde)
    if hasta:
        query = query.filter(model.fecha <= hasta)
    return query


def list_points(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    tipo: Optional[str] = None,
    rubro: Optional[str] = None,
    distrito_id: Optional[int] = None,
) -> List[Dict[str, object]]:
    """
    Devuelve puntos geocodificados (actuaciones + relevamientos).
    """
    d_desde = _parse_date(desde)
    d_hasta = _parse_date(hasta)

    points: List[Dict[str, object]] = []

    # Actuaciones
    q_act = (
        db.session.query(
            Actuaciones.id.label("ref_id"),
            Actuaciones.fecha.label("fecha"),
            Actuaciones.tipo.label("tipo"),
            Domicilio.id.label("domicilio_id"),
            Domicilio.distrito_id.label("distrito_id"),
            Rubro.nombre.label("rubro"),
            DomicilioGeocode.lat.label("lat"),
            DomicilioGeocode.lng.label("lng"),
        )
        .join(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .join(DomicilioGeocode, Domicilio.id == DomicilioGeocode.domicilio_id)
        .outerjoin(Rubro, Domicilio.rubro_id == Rubro.id)
        .filter(DomicilioGeocode.geo_status == "OK")
    )
    q_act = _apply_date_filters(q_act, Actuaciones, d_desde, d_hasta)
    if tipo:
        q_act = q_act.filter(Actuaciones.tipo == tipo)
    if rubro:
        q_act = q_act.filter(Rubro.nombre == rubro)
    if distrito_id:
        q_act = q_act.filter(Domicilio.distrito_id == distrito_id)

    for row in q_act.all():
        points.append(
            {
                "source": "actuaciones",
                "ref_id": row.ref_id,
                "fecha": row.fecha.isoformat() if row.fecha else None,
                "tipo": row.tipo,
                "rubro": row.rubro,
                "domicilio_id": row.domicilio_id,
                "distrito_id": row.distrito_id,
                "lat": float(row.lat) if row.lat is not None else None,
                "lng": float(row.lng) if row.lng is not None else None,
            }
        )

    # Relevamientos
    q_rel = (
        db.session.query(
            Relevamiento.id.label("ref_id"),
            Relevamiento.fecha.label("fecha"),
            Domicilio.id.label("domicilio_id"),
            Domicilio.distrito_id.label("distrito_id"),
            Rubro.nombre.label("rubro"),
            DomicilioGeocode.lat.label("lat"),
            DomicilioGeocode.lng.label("lng"),
        )
        .join(Domicilio, Relevamiento.domicilio_id == Domicilio.id)
        .join(DomicilioGeocode, Domicilio.id == DomicilioGeocode.domicilio_id)
        .outerjoin(Rubro, Domicilio.rubro_id == Rubro.id)
        .filter(DomicilioGeocode.geo_status == "OK")
    )
    q_rel = _apply_date_filters(q_rel, Relevamiento, d_desde, d_hasta)
    if rubro:
        q_rel = q_rel.filter(Rubro.nombre == rubro)
    if distrito_id:
        q_rel = q_rel.filter(Domicilio.distrito_id == distrito_id)

    for row in q_rel.all():
        points.append(
            {
                "source": "relevamientos",
                "ref_id": row.ref_id,
                "fecha": row.fecha.isoformat() if row.fecha else None,
                "tipo": None,
                "rubro": row.rubro,
                "domicilio_id": row.domicilio_id,
                "distrito_id": row.distrito_id,
                "lat": float(row.lat) if row.lat is not None else None,
                "lng": float(row.lng) if row.lng is not None else None,
            }
        )

    return points


def list_points_v2(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    origin: Optional[str] = None,
    tipo: Optional[str] = None,
    contraproducencia: Optional[str] = None,
    rubro_id: Optional[int] = None,
    distrito_id: Optional[int] = None,
) -> List[Dict[str, object]]:
    """
    Devuelve un punto por domicilio con geocode OK + flags de origen.

    Args:
        desde: fecha desde.
        hasta: fecha hasta.
        origin: origen (actuaciones/relevamientos/both).
        tipo: filtro tipo de actuación.
        contraproducencia: filtro de contraproducencia.
        rubro_id: filtro por rubro.
        distrito_id: filtro por distrito.

    Returns:
        Lista de puntos agregados por domicilio.
    """
    d_desde = _parse_date(desde)
    d_hasta = _parse_date(hasta)

    act_q = db.session.query(
        Actuaciones.domicilio_id.label("dom_id"),
        func.count(Actuaciones.id).label("act_count"),
        func.max(Actuaciones.fecha).label("last_act_fecha"),
    ).filter(Actuaciones.domicilio_id.isnot(None))
    act_q = _apply_date_filters(act_q, Actuaciones, d_desde, d_hasta)
    if tipo:
        act_q = act_q.filter(Actuaciones.tipo == tipo)
    if contraproducencia:
        act_q = act_q.filter(Actuaciones.contraproducencia == contraproducencia)
    act_sub = act_q.group_by(Actuaciones.domicilio_id).subquery()

    rel_q = db.session.query(
        Relevamiento.domicilio_id.label("dom_id"),
        func.count(Relevamiento.id).label("rel_count"),
        func.max(Relevamiento.fecha).label("last_rel_fecha"),
    ).filter(Relevamiento.domicilio_id.isnot(None))
    rel_q = _apply_date_filters(rel_q, Relevamiento, d_desde, d_hasta)
    rel_sub = rel_q.group_by(Relevamiento.domicilio_id).subquery()

    q = (
        db.session.query(
            Domicilio.id.label("domicilio_id"),
            DomicilioGeocode.lat,
            DomicilioGeocode.lng,
            DomicilioGeocode.geo_status,
            Domicilio.distrito_id,
            Domicilio.rubro_id,
            act_sub.c.act_count,
            act_sub.c.last_act_fecha,
            rel_sub.c.rel_count,
            rel_sub.c.last_rel_fecha,
        )
        .join(DomicilioGeocode, Domicilio.id == DomicilioGeocode.domicilio_id)
        .outerjoin(act_sub, act_sub.c.dom_id == Domicilio.id)
        .outerjoin(rel_sub, rel_sub.c.dom_id == Domicilio.id)
        .filter(Domicilio.deleted_at.is_(None))
        .filter(DomicilioGeocode.geo_status == "OK")
    )
    if rubro_id:
        q = q.filter(Domicilio.rubro_id == rubro_id)
    if distrito_id:
        q = q.filter(Domicilio.distrito_id == distrito_id)

    if origin:
        if origin == "actuaciones":
            q = q.filter(act_sub.c.act_count.isnot(None))
        elif origin == "relevamientos":
            q = q.filter(rel_sub.c.rel_count.isnot(None))
        elif origin == "both":
            q = q.filter(act_sub.c.act_count.isnot(None)).filter(rel_sub.c.rel_count.isnot(None))
    else:
        q = q.filter(or_(act_sub.c.act_count.isnot(None), rel_sub.c.rel_count.isnot(None)))

    points: List[Dict[str, object]] = []
    for row in q.all():
        points.append(
            {
                "domicilio_id": row.domicilio_id,
                "lat": float(row.lat) if row.lat is not None else None,
                "lng": float(row.lng) if row.lng is not None else None,
                "distrito_id": row.distrito_id,
                "rubro_id": row.rubro_id,
                "has_act": row.act_count is not None,
                "has_rel": row.rel_count is not None,
                "act_count": int(row.act_count) if row.act_count is not None else 0,
                "rel_count": int(row.rel_count) if row.rel_count is not None else 0,
                "last_act_fecha": row.last_act_fecha.isoformat() if row.last_act_fecha else None,
                "last_rel_fecha": row.last_rel_fecha.isoformat() if row.last_rel_fecha else None,
            }
        )
    return points


def get_details(
    domicilio_id: int, desde: Optional[str] = None, hasta: Optional[str] = None
) -> Dict[str, object]:
    """
    Obtiene detalle de domicilio para la card del mapa.

    Args:
        domicilio_id: id del domicilio.
        desde: fecha desde.
        hasta: fecha hasta.

    Returns:
        Dict con datos agregados y listados.

    Raises:
        ValueError: si el domicilio no existe.
    """
    d_desde = _parse_date(desde)
    d_hasta = _parse_date(hasta)

    dom = Domicilio.query.get(domicilio_id)
    if not dom:
        raise ValueError("Domicilio no encontrado.")

    act_q = Actuaciones.query.filter(Actuaciones.domicilio_id == domicilio_id)
    act_q = _apply_date_filters(act_q, Actuaciones, d_desde, d_hasta)
    acts = act_q.order_by(Actuaciones.fecha.desc()).all()

    rel_q = Relevamiento.query.filter(Relevamiento.domicilio_id == domicilio_id)
    rel_q = _apply_date_filters(rel_q, Relevamiento, d_desde, d_hasta)
    rels = rel_q.order_by(Relevamiento.fecha.desc()).all()

    def _act_to_dict(act: Actuaciones) -> Dict[str, object]:
        inspeccion = getattr(act, "inspeccion", None)
        clausura = getattr(act, "clausura", None)
        decomiso = getattr(act, "decomiso", None)
        noti = getattr(act, "notificacion", None)
        comp = getattr(act, "comprobacion", None)

        motivos = []
        if noti:
            rel = getattr(noti, "motivo", None) or getattr(noti, "motivos", None) or []
            for m in rel:
                mn = getattr(m, "nombre", None)
                if mn:
                    motivos.append(mn)

        insp_names = [
            r[0]
            for r in db.session.query(Inspector.nombre)
            .join(actuaciones_inspector, Inspector.id == actuaciones_inspector.c.inspector_id)
            .filter(actuaciones_inspector.c.actuaciones_id == act.id)
            .filter(actuaciones_inspector.c.deleted_at.is_(None))
            .all()
            if r[0]
        ]

        return {
            "id": act.id,
            "fecha": act.fecha.isoformat() if act.fecha else None,
            "tipo": act.tipo,
            "contraproducencia": act.contraproducencia,
            "odt": getattr(act.orden_trabajo, "numero_acta", None) if act.orden_trabajo else None,
            "inspectores": insp_names,
            "acta_inspeccion": getattr(inspeccion, "numero_acta", None) if inspeccion else None,
            "acta_notificacion": getattr(noti, "numero_acta", None) if noti else None,
            "motivos_notificacion": motivos,
            "acta_comprobacion": getattr(comp, "numero_acta", None) if comp else None,
            "acta_clausura": getattr(clausura, "numero_acta", None) if clausura else None,
            "acta_decomiso": getattr(decomiso, "numero_acta", None) if decomiso else None,
            "decomiso_kilos": getattr(decomiso, "cantidad", None) if decomiso else None,
        }

    def _rel_to_dict(rel: Relevamiento) -> Dict[str, object]:
        return {
            "id": rel.id,
            "fecha": rel.fecha.isoformat() if rel.fecha else None,
            "inspector": rel.inspector.nombre if rel.inspector else None,
            "rubro": rel.rubro.nombre if rel.rubro else None,
            "contraproducencia": rel.contraproducencia,
        }

    contrib = dom.contribuyente
    contrib_str = None
    if contrib:
        parts = [contrib.apellido, contrib.nombre, contrib.documento or contrib.doc_nro]
        contrib_str = " ".join([p for p in parts if p])

    return {
        "domicilio_id": dom.id,
        "calle": dom.calle_normalizada or dom.calle,
        "numero": dom.numero,
        "esquina": dom.esquina_normalizada,
        "act_count": len(acts),
        "rel_count": len(rels),
        "last_act_fecha": acts[0].fecha.isoformat() if acts else None,
        "last_rel_fecha": rels[0].fecha.isoformat() if rels else None,
        "rubro": dom.rubro.nombre if dom.rubro else None,
        "contribuyente": contrib_str,
        "odt_list": list(
            {
                a.orden_trabajo.numero_acta
                for a in acts
                if a.orden_trabajo and a.orden_trabajo.numero_acta
            }
        ),
        "actuaciones": [_act_to_dict(a) for a in acts],
        "relevamientos": [_rel_to_dict(r) for r in rels],
    }


def list_heatmap(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    tipo: Optional[str] = None,
    rubro: Optional[str] = None,
    distrito_id: Optional[int] = None,
    metrica: Optional[str] = None,
) -> List[Dict[str, object]]:
    points = list_points(desde, hasta, tipo, rubro, distrito_id)
    return [{"lat": p["lat"], "lng": p["lng"], "weight": 1} for p in points]


def list_distritos_metric(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    tipo: Optional[str] = None,
    rubro: Optional[str] = None,
) -> List[Dict[str, object]]:
    points = list_points(desde, hasta, tipo, rubro, None)
    counter: Dict[int, int] = {}
    for p in points:
        did = p.get("distrito_id")
        if not did:
            continue
        counter[int(did)] = counter.get(int(did), 0) + 1

    items: List[Dict[str, object]] = []
    for did, value in counter.items():
        distrito = Distrito.query.get(did)
        items.append(
            {
                "distrito_id": did,
                "nombre": distrito.nombre if distrito else None,
                "value": value,
            }
        )
    return items


def list_pendientes(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    scope: Optional[str] = None,
) -> List[Dict[str, object]]:
    d_desde = _parse_date(desde)
    d_hasta = _parse_date(hasta)

    act_subq = (
        db.session.query(
            Actuaciones.domicilio_id.label("dom_id"),
            func.max(Actuaciones.id).label("last_act_id"),
            func.count(Actuaciones.id).label("act_count"),
        )
        .group_by(Actuaciones.domicilio_id)
        .subquery()
    )
    rel_subq = (
        db.session.query(
            Relevamiento.domicilio_id.label("dom_id"),
            func.max(Relevamiento.id).label("last_rel_id"),
            func.count(Relevamiento.id).label("rel_count"),
        )
        .group_by(Relevamiento.domicilio_id)
        .subquery()
    )

    q = (
        db.session.query(
            Domicilio,
            DomicilioGeocode.geo_status,
            DomicilioGeocode.error_msg,
            DomicilioGeocode.lat,
            DomicilioGeocode.lng,
            act_subq.c.last_act_id,
            act_subq.c.act_count,
            rel_subq.c.last_rel_id,
            rel_subq.c.rel_count,
        )
        .outerjoin(DomicilioGeocode, Domicilio.id == DomicilioGeocode.domicilio_id)
        .outerjoin(act_subq, act_subq.c.dom_id == Domicilio.id)
        .outerjoin(rel_subq, rel_subq.c.dom_id == Domicilio.id)
        .filter(Domicilio.deleted_at.is_(None))
    )

    norm_pending = or_(
        Domicilio.calle_norm_status.is_(None),
        Domicilio.calle_norm_status != "OK",
        and_(
            Domicilio.numero_tipo == "ESQUINA",
            or_(Domicilio.esquina_norm_status.is_(None), Domicilio.esquina_norm_status != "OK"),
        ),
    )
    geo_pending = or_(
        DomicilioGeocode.domicilio_id.is_(None),
        DomicilioGeocode.geo_status != "OK",
    )
    latlon_pending = or_(
        DomicilioGeocode.lat.is_(None),
        DomicilioGeocode.lng.is_(None),
    )
    q = q.filter(or_(norm_pending, geo_pending, latlon_pending))

    if scope in {"actuaciones", "relevamientos"}:
        if scope == "actuaciones":
            q = q.filter(act_subq.c.last_act_id.isnot(None))
        else:
            q = q.filter(rel_subq.c.last_rel_id.isnot(None))

    results = []
    for dom, geo_status, error_msg, lat, lng, last_act_id, act_count, last_rel_id, rel_count in q.all():
        results.append(
            {
                "domicilio_id": dom.id,
                "calle_raw": dom.calle,
                "calle_normalizada": dom.calle_normalizada,
                "numero_raw": dom.numero,
                "numero_tipo": dom.numero_tipo,
                "esquina_normalizada": dom.esquina_normalizada,
                "calle_status": dom.calle_norm_status,
                "esquina_status": dom.esquina_norm_status,
                "geo_status": geo_status,
                "error_msg": error_msg,
                "lat": float(lat) if lat is not None else None,
                "lng": float(lng) if lng is not None else None,
                "last_actuacion_id": last_act_id,
                "actuaciones_count": act_count or 0,
                "last_relevamiento_id": last_rel_id,
                "relevamientos_count": rel_count or 0,
            }
        )
    return results
