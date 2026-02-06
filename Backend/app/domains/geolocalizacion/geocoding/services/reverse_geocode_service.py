from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Dict, Optional, Tuple


GEO_PROVIDER = os.getenv("GEOCODER_PROVIDER", os.getenv("GEO_PROVIDER", "nominatim")).lower()

GEOAPIFY_REVERSE_URL = "https://api.geoapify.com/v1/geocode/reverse"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
TIMEOUT_SEC = 25
USER_AGENT = "proyecto_pratica_geocode/1.0 (local)"


def _reverse_geoapify(lat: float, lon: float) -> Dict[str, object]:
    api_key = os.getenv("GEOAPIFY_API_KEY")
    if not api_key:
        raise ValueError("GEOAPIFY_API_KEY no configurada.")
    params = {
        "lat": lat,
        "lon": lon,
        "apiKey": api_key,
        "format": "geojson",
        "limit": 1,
    }
    url = f"{GEOAPIFY_REVERSE_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) or {}


def _reverse_nominatim(lat: float, lon: float) -> Dict[str, object]:
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
    }
    url = f"{NOMINATIM_REVERSE_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) or {}


def reverse_geocode(lat: float, lon: float) -> Dict[str, object]:
    """
    Reverse geocode según provider configurado.

    Args:
        lat: latitud.
        lon: longitud.

    Returns:
        Dict con provider, raw, road y house_number.

    Raises:
        ValueError: si falta API key en Geoapify.
    """
    provider = GEO_PROVIDER if GEO_PROVIDER in {"geoapify", "nominatim"} else "nominatim"
    if provider == "geoapify":
        data = _reverse_geoapify(lat, lon)
        features = data.get("features") or []
        if not features:
            return {"provider": provider, "raw": data, "road": None, "house_number": None}
        props = features[0].get("properties") or {}
        road = props.get("street") or props.get("road")
        house_number = props.get("housenumber") or props.get("house_number")
        return {
            "provider": provider,
            "raw": features[0],
            "road": road,
            "house_number": house_number,
        }
    data = _reverse_nominatim(lat, lon)
    address = data.get("address") or {}
    road = address.get("road") or address.get("pedestrian") or address.get("footway")
    house_number = address.get("house_number")
    return {
        "provider": provider,
        "raw": data,
        "road": road,
        "house_number": house_number,
    }
