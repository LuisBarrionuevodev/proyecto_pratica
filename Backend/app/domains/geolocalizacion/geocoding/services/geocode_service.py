from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional
import json
import os
import urllib.parse
import urllib.request

from app.database import db
from app.models import Domicilio
from app.domains.geolocalizacion.geocoding.repos.domicilio_geocode_repo import (
    get_or_create_geocode,
)


GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode/search"
GEOAPIFY_TIMEOUT_SEC = 25
GEOAPIFY_USER_AGENT = "proyecto_pratica_geocode/1.0 (local)"


def _can_geocode(dom: Domicilio) -> tuple[bool, Optional[str]]:
    """
    Verifica si el domicilio está normalizado para geocodificar.

    Reglas:
    - calle_norm_status debe ser OK
    - si numero_tipo == ESQUINA, esquina_norm_status debe ser OK
    """
    if dom.calle_norm_status != "OK":
        return False, "not normalized"
    if dom.numero_tipo == "ESQUINA" and dom.esquina_norm_status != "OK":
        return False, "not normalized"
    return True, None


def _build_query(dom: Domicilio) -> str:
    """
    Construye el query de geocoding para Nominatim.
    """
    calle = dom.calle_normalizada or dom.calle
    esquina_raw = getattr(dom, "esquina_raw", None)
    if dom.numero_tipo == "ESQUINA" and (esquina_raw or dom.esquina_normalizada):
        esquina = esquina_raw or dom.esquina_normalizada
        q = f"{calle} y {esquina}, San Miguel de Tucumán, Tucumán, Argentina"
    else:
        q = f"{calle} {dom.numero}, San Miguel de Tucumán, Tucumán, Argentina"
    return q


def _build_query_no_number(dom: Domicilio) -> str:
    """
    Fallback: query solo con calle (sin número).
    """
    calle = dom.calle_normalizada or dom.calle
    return f"{calle}, San Miguel de Tucumán, Tucumán, Argentina"


def _request_geoapify(query: str) -> dict:
    """
    Ejecuta la búsqueda en Geoapify con timeout corto y 1 retry.
    """
    api_key = os.getenv("GEOAPIFY_API_KEY")
    if not api_key:
        raise ValueError("GEOAPIFY_API_KEY no configurada.")
    params = {
        "text": query,
        "apiKey": api_key,
        "format": "geojson",
        "limit": 1,
    }
    url = f"{GEOAPIFY_URL}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": GEOAPIFY_USER_AGENT}
    last_error: Exception | None = None
    for _ in range(2):
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=GEOAPIFY_TIMEOUT_SEC) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) or {}
        except Exception as exc:  # noqa: BLE001 - se reporta como ERROR
            last_error = exc
    if last_error:
        raise last_error
    return {}


def _evaluate_result(feature: dict) -> Dict[str, object]:
    """
    Evalúa un resultado de Geoapify y define status/quality/score.
    """
    props = feature.get("properties") or {}
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    lng = float(coords[0]) if len(coords) > 1 else None
    lat = float(coords[1]) if len(coords) > 1 else None
    result_type = str(props.get("result_type") or "")
    confidence = props.get("rank", {}).get("confidence")
    status = "REVIEW" if result_type in {"city", "street", "district"} else "OK"
    quality = result_type[:30] if result_type else None
    score = confidence

    return {
        "status": status,
        "lat": lat,
        "lng": lng,
        "quality": quality,
        "score": score,
    }


def geocode_domicilio(domicilio_id: int) -> Dict[str, object]:
    """
    Geocodifica un domicilio y persiste el resultado en `domicilio_geocode`.

    Args:
        domicilio_id: id del domicilio.

    Returns:
        Dict con estado, coordenadas y metadata del proveedor.

    Raises:
        ValueError: si el domicilio no existe.
    """
    dom = db.session.get(Domicilio, domicilio_id)
    if not dom:
        raise ValueError("Domicilio no encontrado.")

    can_geocode, reason = _can_geocode(dom)
    if not can_geocode:
        return {
            "ok": False,
            "status": "SKIP",
            "reason": reason,
            "domicilio_id": domicilio_id,
        }

    geo = get_or_create_geocode(domicilio_id)
    geo.provider = "geoapify"
    geo.checked_at = datetime.utcnow()

    try:
        query = _build_query(dom)
        response = _request_geoapify(query)
        features = response.get("features") or []
        used_fallback = False
        fallback_query = None
        if not features:
            # fallback sin número
            fallback_query = _build_query_no_number(dom)
            used_fallback = True
            response = _request_geoapify(fallback_query)
            features = response.get("features") or []
        if not features:
            geo.geo_status = "NO_MATCH"
            geo.lat = None
            geo.lng = None
            geo.quality = None
            geo.score = None
            geo.error_msg = "no match"
            geo.raw_json = None
        else:
            feature = features[0]
            evaluated = _evaluate_result(feature)
            # Si llegó por fallback, degradamos a REVIEW para evitar falso OK
            geo.geo_status = "REVIEW" if used_fallback else evaluated["status"]
            geo.lat = evaluated["lat"]
            geo.lng = evaluated["lng"]
            geo.quality = evaluated["quality"]
            geo.score = evaluated["score"]
            geo.error_msg = None
            geo.raw_json = feature
    except Exception as exc:  # noqa: BLE001 - se reporta como ERROR
        geo.geo_status = "ERROR"
        geo.lat = None
        geo.lng = None
        geo.quality = None
        geo.score = None
        geo.error_msg = str(exc)[:255]
        geo.raw_json = None

    db.session.add(geo)
    db.session.commit()

    return {
        "ok": geo.geo_status in {"OK", "REVIEW"},
        "domicilio_id": domicilio_id,
        "geo_status": geo.geo_status,
        "lat": float(geo.lat) if geo.lat is not None else None,
        "lng": float(geo.lng) if geo.lng is not None else None,
        "provider": geo.provider,
        "checked_at": geo.checked_at.isoformat() if geo.checked_at else None,
        "error_msg": geo.error_msg,
        "query": query,
        "fallback_query": fallback_query,
        "used_fallback": used_fallback,
    }
