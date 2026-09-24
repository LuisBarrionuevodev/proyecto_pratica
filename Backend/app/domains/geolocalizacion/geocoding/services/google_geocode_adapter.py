"""
GEO-GOOGLE.2 — adaptador productivo Google Geocoding.

Produce resultados canónicos para ``geocode_domicilio`` sin reglas Geoapify
(``building`` / ``score >= 0.95``).
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from app.models import Domicilio

logger = logging.getLogger(__name__)

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GOOGLE_TIMEOUT_SEC = 25
SMT_SUFFIX = "San Miguel de Tucumán, Tucumán, Argentina"

GOOGLE_API_ERROR_STATUSES = frozenset(
    {"REQUEST_DENIED", "OVER_QUERY_LIMIT", "INVALID_REQUEST", "UNKNOWN_ERROR"}
)
GOOGLE_RECOVERABLE_STATUSES = frozenset({"ZERO_RESULTS", "OVER_QUERY_LIMIT", "UNKNOWN_ERROR"})

LOCATION_TYPE_TO_PRECISION = {
    "ROOFTOP": "ROOFTOP",
    "RANGE_INTERPOLATED": "INTERPOLATED",
    "GEOMETRIC_CENTER": "GEOMETRIC_CENTER",
    "APPROXIMATE": "APPROXIMATE",
}


@dataclass(frozen=True)
class GeocodeResult:
    """Resultado canónico de geocodificación Google."""

    lat: Optional[float]
    lng: Optional[float]
    provider: str
    provider_place_id: Optional[str]
    precision: Optional[str]
    confidence: Optional[float]
    formatted_address: Optional[str]
    partial_match: Optional[bool]
    raw_status: str
    geo_status: str
    error_msg: Optional[str] = None
    raw_payload: Optional[dict[str, Any]] = None
    query_used: Optional[str] = None


def _redact_secret(text: str, secret: str) -> str:
    if not secret or not text:
        return text
    return text.replace(secret, "***")


def get_google_maps_api_key() -> Optional[str]:
    """
    Lee GOOGLE_MAPS_API_KEY del entorno (solo backend).

    Returns:
        Key sin espacios o None si falta.
    """
    return (
        os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_GEOCODING_API_KEY") or ""
    ).strip() or None


def google_can_attempt(dom: Domicilio) -> bool:
    """
    Indica si hay texto suficiente para intentar Google (incluye RAW sin catálogo SMT).

    Args:
        dom: domicilio a evaluar.

    Returns:
        True si se puede armar al menos un query.
    """
    calle = (dom.calle_normalizada or dom.calle or "").strip()
    if not calle:
        return False
    if dom.numero_tipo == "ESQUINA":
        esquina = (
            dom.esquina_normalizada
            or getattr(dom, "esquina_raw", None)
            or dom.numero
            or ""
        ).strip()
        return bool(esquina)
    return bool((dom.numero or "").strip())


def _street_for_query(dom: Domicilio, *, prefer_normalized: bool) -> str:
    if prefer_normalized and dom.calle_norm_status == "OK" and dom.calle_normalizada:
        return dom.calle_normalizada.strip()
    return (dom.calle or dom.calle_normalizada or "").strip()


def _esquina_for_query(dom: Domicilio, *, prefer_normalized: bool) -> str:
    if prefer_normalized and dom.esquina_norm_status == "OK" and dom.esquina_normalizada:
        return dom.esquina_normalizada.strip()
    return (
        dom.esquina_normalizada
        or getattr(dom, "esquina_raw", None)
        or dom.numero
        or ""
    ).strip()


def build_google_queries(dom: Domicilio) -> list[str]:
    """
    Arma queries Google para NUMERO o ESQUINA.

    Prefiere dirección normalizada SMT; si el catálogo falló, incluye query RAW.
    No altera identidad DB ante formatted_address invertido de Google.

    Args:
        dom: domicilio fuente.

    Returns:
        Lista deduplicada de queries a intentar en orden.
    """
    queries: list[str] = []
    seen: set[str] = set()

    def _add(q: str) -> None:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            queries.append(q)

    if dom.numero_tipo == "ESQUINA":
        for prefer_norm in (True, False):
            calle = _street_for_query(dom, prefer_normalized=prefer_norm)
            esquina = _esquina_for_query(dom, prefer_normalized=prefer_norm)
            if calle and esquina:
                _add(f"{calle} y {esquina}, {SMT_SUFFIX}")
    else:
        numero = (dom.numero or "").strip()
        if not numero:
            return queries
        for prefer_norm in (True, False):
            calle = _street_for_query(dom, prefer_normalized=prefer_norm)
            if calle:
                _add(f"{calle} {numero}, {SMT_SUFFIX}")
    return queries


def normalize_google_response(data: dict[str, Any], query: str) -> dict[str, Any]:
    """
    Normaliza JSON de Google Geocoding API.

    Args:
        data: respuesta cruda.
        query: query enviada.

    Returns:
        Dict canónico intermedio.
    """
    api_status = str(data.get("status") or "UNKNOWN")
    results = data.get("results") or []
    if not results:
        return {
            "provider": "google",
            "lat": None,
            "lng": None,
            "place_id": None,
            "formatted_address": None,
            "location_type": None,
            "partial_match": None,
            "status": api_status,
            "query": query,
            "raw": data,
        }
    r0 = results[0]
    geom = r0.get("geometry") or {}
    loc = geom.get("location") or {}
    return {
        "provider": "google",
        "lat": loc.get("lat"),
        "lng": loc.get("lng"),
        "place_id": r0.get("place_id"),
        "formatted_address": r0.get("formatted_address"),
        "location_type": geom.get("location_type"),
        "partial_match": bool(r0.get("partial_match")),
        "status": api_status,
        "query": query,
        "raw": data,
    }


def request_google_geocode(query: str, api_key: str) -> dict[str, Any]:
    """
    Ejecuta request a Google Geocoding API.

    Args:
        query: dirección.
        api_key: GOOGLE_MAPS_API_KEY (no loguear).

    Returns:
        Respuesta normalizada.

    Raises:
        ValueError: si falta api key.
        urllib.error.HTTPError: error HTTP.
        urllib.error.URLError: error de red.
    """
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY no configurada.")
    params = {
        "address": query,
        "key": api_key,
        "region": "ar",
        "language": "es",
    }
    url = GOOGLE_GEOCODE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=GOOGLE_TIMEOUT_SEC) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    return normalize_google_response(raw, query)


def map_location_type_to_precision(location_type: Optional[str]) -> Optional[str]:
    """Mapea location_type Google a precision canónica."""
    if not location_type:
        return None
    return LOCATION_TYPE_TO_PRECISION.get(str(location_type).upper())


def evaluate_google_geo_status(
    numero_tipo: Optional[str],
    precision: Optional[str],
    partial_match: Optional[bool],
) -> str:
    """
    Regla GEO-REVIEW.1: resultado Google con coordenadas utilizables → ``OK``.

    ``precision``, ``partial_match`` y ``numero_tipo`` son metadata de display;
    no afectan revisión manual. Llamar solo cuando ``lat``/``lng`` ya están validados.

    Args:
        numero_tipo: NUMERO | ESQUINA | etc. (metadata).
        precision: ROOFTOP | INTERPOLATED | GEOMETRIC_CENTER | APPROXIMATE (metadata).
        partial_match: flag Google (metadata).

    Returns:
        ``OK``.
    """
    _ = numero_tipo, precision, partial_match
    return "OK"


def normalized_to_geocode_result(
    normalized: dict[str, Any],
    *,
    numero_tipo: Optional[str],
    query_used: str,
    error_msg: Optional[str] = None,
) -> GeocodeResult:
    """
    Convierte respuesta normalizada a GeocodeResult productivo.

    Args:
        normalized: salida de ``normalize_google_response``.
        numero_tipo: tipo de numeración del domicilio.
        query_used: query efectiva.
        error_msg: mensaje de error seguro (sin secretos).

    Returns:
        GeocodeResult con geo_status persistible.
    """
    api_status = str(normalized.get("status") or "UNKNOWN").upper()
    lat_raw = normalized.get("lat")
    lng_raw = normalized.get("lng")
    lat = float(lat_raw) if lat_raw is not None else None
    lng = float(lng_raw) if lng_raw is not None else None
    precision = map_location_type_to_precision(normalized.get("location_type"))
    partial_match = normalized.get("partial_match")

    if api_status in GOOGLE_API_ERROR_STATUSES:
        return GeocodeResult(
            lat=None,
            lng=None,
            provider="google",
            provider_place_id=None,
            precision=None,
            confidence=None,
            formatted_address=None,
            partial_match=None,
            raw_status=api_status,
            geo_status="ERROR",
            error_msg=error_msg or api_status,
            raw_payload=normalized.get("raw"),
            query_used=query_used,
        )

    if api_status == "ZERO_RESULTS" or lat is None or lng is None:
        return GeocodeResult(
            lat=None,
            lng=None,
            provider="google",
            provider_place_id=None,
            precision=None,
            confidence=None,
            formatted_address=normalized.get("formatted_address"),
            partial_match=partial_match,
            raw_status=api_status,
            geo_status="NO_MATCH",
            error_msg=error_msg or "no match",
            raw_payload=normalized.get("raw"),
            query_used=query_used,
        )

    geo_status = evaluate_google_geo_status(numero_tipo, precision, partial_match)
    from app.domains.geolocalizacion.geocoding.services.geocode_confidence import (
        google_precision_to_display_score,
    )

    display_score = google_precision_to_display_score(precision)
    return GeocodeResult(
        lat=lat,
        lng=lng,
        provider="google",
        provider_place_id=normalized.get("place_id"),
        precision=precision,
        confidence=display_score,
        formatted_address=normalized.get("formatted_address"),
        partial_match=partial_match,
        raw_status=api_status,
        geo_status=geo_status,
        error_msg=None,
        raw_payload=normalized.get("raw"),
        query_used=query_used,
    )


def geocode_google_for_domicilio(dom: Domicilio) -> GeocodeResult:
    """
    Geocodifica un domicilio con Google probando queries en orden.

    Args:
        dom: domicilio con texto de dirección.

    Returns:
        Mejor GeocodeResult (primer OK con coords, o último intento).

    Raises:
        ValueError: si falta API key.
    """
    api_key = get_google_maps_api_key()
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY no configurada.")

    queries = build_google_queries(dom)
    if not queries:
        return GeocodeResult(
            lat=None,
            lng=None,
            provider="google",
            provider_place_id=None,
            precision=None,
            confidence=None,
            formatted_address=None,
            partial_match=None,
            raw_status="SKIP",
            geo_status="NO_MATCH",
            error_msg="no query",
            raw_payload=None,
            query_used=None,
        )

    last_result: Optional[GeocodeResult] = None
    for query in queries:
        try:
            normalized = request_google_geocode(query, api_key)
            result = normalized_to_geocode_result(
                normalized,
                numero_tipo=dom.numero_tipo,
                query_used=query,
            )
        except urllib.error.HTTPError as exc:
            safe = _redact_secret(f"HTTP {exc.code}", api_key)
            result = GeocodeResult(
                lat=None,
                lng=None,
                provider="google",
                provider_place_id=None,
                precision=None,
                confidence=None,
                formatted_address=None,
                partial_match=None,
                raw_status="HTTP_ERROR",
                geo_status="ERROR",
                error_msg=safe[:255],
                raw_payload=None,
                query_used=query,
            )
        except urllib.error.URLError as exc:
            safe = _redact_secret(str(exc.reason), api_key)
            result = GeocodeResult(
                lat=None,
                lng=None,
                provider="google",
                provider_place_id=None,
                precision=None,
                confidence=None,
                formatted_address=None,
                partial_match=None,
                raw_status="NETWORK",
                geo_status="ERROR",
                error_msg=safe[:255],
                raw_payload=None,
                query_used=query,
            )
        except Exception as exc:  # noqa: BLE001
            safe = _redact_secret(str(exc)[:200], api_key)
            result = GeocodeResult(
                lat=None,
                lng=None,
                provider="google",
                provider_place_id=None,
                precision=None,
                confidence=None,
                formatted_address=None,
                partial_match=None,
                raw_status="NETWORK",
                geo_status="ERROR",
                error_msg=safe[:255],
                raw_payload=None,
                query_used=query,
            )

        last_result = result
        if result.geo_status == "OK" and result.lat is not None and result.lng is not None:
            return result
        if result.raw_status not in GOOGLE_RECOVERABLE_STATUSES and result.geo_status == "ERROR":
            return result

    return last_result or GeocodeResult(
        lat=None,
        lng=None,
        provider="google",
        provider_place_id=None,
        precision=None,
        confidence=None,
        formatted_address=None,
        partial_match=None,
        raw_status="ZERO_RESULTS",
        geo_status="NO_MATCH",
        error_msg="no match",
        raw_payload=None,
        query_used=queries[-1] if queries else None,
    )


def is_google_recoverable_failure(result: GeocodeResult) -> bool:
    """True si conviene intentar fallback provider (p.ej. Geoapify)."""
    if result.geo_status == "OK":
        return False
    if result.geo_status == "NO_MATCH":
        return True
    return result.raw_status in GOOGLE_RECOVERABLE_STATUSES or result.geo_status == "ERROR"


def log_google_shadow_metrics(dom_id: int, result: GeocodeResult) -> None:
    """Registra métricas shadow sin alterar persistencia productiva."""
    logger.info(
        "google_shadow domicilio_id=%s status=%s precision=%s partial=%s lat=%s lng=%s",
        dom_id,
        result.raw_status,
        result.precision,
        result.partial_match,
        result.lat,
        result.lng,
    )
