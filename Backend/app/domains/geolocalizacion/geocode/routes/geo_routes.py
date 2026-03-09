from __future__ import annotations

from typing import Any, Dict
from datetime import datetime

from flask import jsonify, request
from sqlalchemy import and_

from app.database import db
from app.models import Domicilio
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    on_domicilio_changed,
    compute_addr_hash,
)
from app.domains.geolocalizacion.geocoding.repos.domicilio_geocode_repo import (
    get_or_create_geocode,
)
from app.domains.geolocalizacion.geocoding.services.reverse_geocode_service import (
    reverse_geocode,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio_en_sesion,
)

from . import geolocalizacion_map


@geolocalizacion_map.get("/geo/pending")
def geo_pending():
    """
    Lista domicilios con geocoding pendiente o fallido.

    Returns:
        JSON con items pendientes.
    """
    q = (
        Domicilio.query.outerjoin(
            DomicilioGeocode,
            and_(
                Domicilio.id == DomicilioGeocode.domicilio_id,
                DomicilioGeocode.deleted_at.is_(None),
            ),
        )
        .filter(Domicilio.deleted_at.is_(None))
        .filter(
            (DomicilioGeocode.domicilio_id.is_(None))
            | (DomicilioGeocode.geo_status.in_(["PENDING", "REVIEW", "NO_MATCH", "ERROR"]))
        )
    )
    items = []
    for dom, geo in q.add_entity(DomicilioGeocode).all():
        items.append(
            {
                "domicilio_id": dom.id,
                "calle_normalizada": dom.calle_normalizada,
                "numero": dom.numero,
                "esquina_normalizada": dom.esquina_normalizada,
                "ciudad": dom.ciudad,
                "rubro_id": dom.rubro_id,
                "contribuyente_id": dom.contribuyente_id,
                "geo_status": geo.geo_status if geo else None,
                "error_msg": geo.error_msg if geo else None,
                "checked_at": geo.checked_at.isoformat() if geo and geo.checked_at else None,
            }
        )
    return jsonify({"items": items}), 200


@geolocalizacion_map.post("/geo/<int:domicilio_id>/retry")
def geo_retry(domicilio_id: int):
    """
    Fuerza re-geocode para un domicilio.

    Args:
        domicilio_id: id del domicilio.

    Returns:
        Resultado del orquestador.

    Errors:
        400 si el domicilio no existe.
    """
    try:
        result = on_domicilio_changed(domicilio_id, force=True)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500


@geolocalizacion_map.post("/geo/<int:domicilio_id>/manual")
def geo_manual(domicilio_id: int):
    """
    Guarda lat/lng manual y marca geocode OK.

    Args:
        domicilio_id: id del domicilio.

    Body:
        lat, lng.

    Returns:
        ok True.
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        return jsonify({"detail": "lat y lng son obligatorios"}), 400
    try:
        dom = db.session.get(Domicilio, domicilio_id)
        if not dom or dom.deleted_at is not None:
            return jsonify({"detail": "Domicilio no encontrado"}), 404
        geo = get_or_create_geocode(domicilio_id)
        geo.lat = lat
        geo.lng = lng
        geo.geo_status = "OK"
        geo.quality = "MANUAL_EXACT"
        geo.source = "MANUAL"
        geo.error_msg = None
        geo.addr_hash = compute_addr_hash(dom)
        geo.checked_at = datetime.utcnow()
        db.session.add(geo)
        db.session.commit()
        return jsonify({"ok": True, "domicilio_id": domicilio_id}), 200
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500


@geolocalizacion_map.post("/geo/<int:domicilio_id>/reverse")
def geo_reverse(domicilio_id: int):
    """
    Reverse geocode: actualiza domicilio y geocode con source REVERSE.

    Args:
        domicilio_id: id del domicilio.

    Body:
        lat, lng.

    Returns:
        ok True.

    Errors:
        400 si no hay road/house_number.
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        return jsonify({"detail": "lat y lng son obligatorios"}), 400
    try:
        dom = db.session.get(Domicilio, domicilio_id)
        if not dom or dom.deleted_at is not None:
            return jsonify({"detail": "Domicilio no encontrado"}), 404

        rev = reverse_geocode(float(lat), float(lng))
        road = rev.get("road")
        house_number = rev.get("house_number")
        if not road or not house_number:
            return jsonify({"detail": "Reverse sin road/house_number", "raw": rev.get("raw")}), 400

        dom.calle = road
        dom.numero = str(house_number)
        dom.numero_tipo = "NUMERO"
        dom.esquina_raw = None
        dom.esquina_catalogo_id = None
        dom.esquina_normalizada = None
        dom.esquina_norm_status = None
        dom.esquina_norm_score = None
        dom.esquina_norm_error = None
        dom.esquina_norm_updated_at = None

        normalizar_domicilio_en_sesion(dom, override_numero_tipo="NUMERO")
        db.session.add(dom)

        geo = get_or_create_geocode(domicilio_id)
        geo.lat = float(lat)
        geo.lng = float(lng)
        geo.geo_status = "OK"
        geo.quality = "REVERSE"
        geo.source = "REVERSE"
        geo.error_msg = None
        geo.raw_json = rev.get("raw")
        geo.addr_hash = compute_addr_hash(dom)
        geo.checked_at = datetime.utcnow()
        db.session.add(geo)
        db.session.commit()
        return jsonify({"ok": True, "domicilio_id": domicilio_id}), 200
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
