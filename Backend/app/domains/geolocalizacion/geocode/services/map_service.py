from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import and_, func, or_

from app.database import db
from app.models import Actuaciones, Domicilio, DomicilioGeocode, Relevamiento, Rubro, Distrito


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
