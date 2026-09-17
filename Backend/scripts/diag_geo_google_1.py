"""
GEO-GOOGLE.1 — PoC: benchmark Google Geocoding vs Geoapify (domicilios reales).

Solo lectura de Digitaliza + requests externos + reporte diagnóstico.
NO modifica domicilio_geocode ni pipeline productivo.

Uso:
    cd Backend
    python scripts/diag_geo_google_1.py --sample-size 100
    python scripts/diag_geo_google_1.py --sample-size 50 --output-dir scripts/output

Requiere en .env:
    GOOGLE_MAPS_API_KEY
    GEOAPIFY_API_KEY  (comparación)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app import create_app
from app.database import db
from app.domains.geolocalizacion.geocoding.services.geocode_service import (
    _evaluate_geoapify,
    _request_geoapify,
)
from app.models import Domicilio, DomicilioGeocode

SMT_SUFFIX = "San Miguel de Tucumán, Tucumán, Argentina"
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
REQUEST_PAUSE_SEC = 0.25

STRATUM_TARGETS = {
    "NUMERO": 40,
    "ESQUINA": 20,
    "NORM_PENDING": 20,
    "GEO_PENDING": 10,
    "MANUAL": 10,
}

LOCATION_TYPE_HIGH = frozenset({"ROOFTOP"})
LOCATION_TYPE_MEDIUM = frozenset({"RANGE_INTERPOLATED"})
LOCATION_TYPE_LOW = frozenset({"GEOMETRIC_CENTER", "APPROXIMATE"})


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia en metros entre dos puntos WGS84."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def _latency_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "p50": 0, "p95": 0, "max": 0, "mean": 0}
    return {
        "n": len(values),
        "p50": round(_percentile(values, 50), 1),
        "p95": round(_percentile(values, 95), 1),
        "max": round(max(values), 1),
        "mean": round(statistics.mean(values), 1),
    }


def _distance_buckets(distances: list[float]) -> dict[str, Any]:
    if not distances:
        return {"n": 0}
    n = len(distances)
    return {
        "n": n,
        "pct_le_20m": round(100 * sum(1 for d in distances if d <= 20) / n, 1),
        "pct_le_50m": round(100 * sum(1 for d in distances if d <= 50) / n, 1),
        "pct_le_100m": round(100 * sum(1 for d in distances if d <= 100) / n, 1),
        "pct_gt_100m": round(100 * sum(1 for d in distances if d > 100) / n, 1),
        "median_m": round(statistics.median(distances), 1),
    }


def _normalize_google_result(data: dict[str, Any], query: str) -> dict[str, Any]:
    """
    Normaliza respuesta Google Geocoding API a formato canónico del PoC.

    Args:
        data: JSON de Google Geocoding API.
        query: query enviada (solo diagnóstico).

    Returns:
        Dict canónico; status API en ``status``.
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
    }


def _normalize_geoapify_result(resp: dict[str, Any], query: str) -> dict[str, Any]:
    """Normaliza respuesta Geoapify a formato comparable del PoC."""
    features = resp.get("features") or []
    if not features:
        return {
            "provider": "geoapify",
            "lat": None,
            "lng": None,
            "place_id": None,
            "formatted_address": None,
            "location_type": None,
            "partial_match": None,
            "status": "NO_MATCH",
            "quality": None,
            "score": None,
            "query": query,
        }
    ev = _evaluate_geoapify(features[0])
    props = (features[0].get("properties") or {})
    return {
        "provider": "geoapify",
        "lat": ev.get("lat"),
        "lng": ev.get("lng"),
        "place_id": props.get("place_id"),
        "formatted_address": props.get("formatted"),
        "location_type": props.get("result_type"),
        "partial_match": None,
        "status": "OK",
        "quality": ev.get("quality"),
        "score": ev.get("score"),
        "query": query,
    }


def _request_google(query: str, api_key: str) -> tuple[dict[str, Any], float]:
    """
    Llama Google Geocoding API (server-side).

    Args:
        query: dirección a geocodificar.
        api_key: GOOGLE_MAPS_API_KEY (nunca loguear).

    Returns:
        (respuesta normalizada, latencia_ms).
    """
    params = {
        "address": query,
        "key": api_key,
        "region": "ar",
        "language": "es",
    }
    url = GOOGLE_GEOCODE_URL + "?" + urllib.parse.urlencode(params)
    t0 = time.perf_counter()
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    ms = (time.perf_counter() - t0) * 1000.0
    return _normalize_google_result(raw, query), ms


def _request_geoapify_timed(query: str) -> tuple[dict[str, Any], float]:
    """Llama Geoapify y retorna resultado normalizado + latencia."""
    t0 = time.perf_counter()
    resp = _request_geoapify(query)
    ms = (time.perf_counter() - t0) * 1000.0
    return _normalize_geoapify_result(resp, query), ms


def _precision_tier(location_type: Optional[str]) -> str:
    """Clasificación orientativa de precisión (solo benchmark)."""
    if not location_type:
        return "unknown"
    lt = str(location_type).upper()
    if lt in LOCATION_TYPE_HIGH or lt == "BUILDING":
        return "alta"
    if lt in LOCATION_TYPE_MEDIUM:
        return "media"
    if lt in LOCATION_TYPE_LOW:
        return "baja"
    return "unknown"


def _classify_operational(
    result: dict[str, Any],
    *,
    golden_lat: Optional[float],
    golden_lng: Optional[float],
) -> str:
    """
    Clasificación operativa del benchmark: AUTO_BUENO | REVISION | MANUAL.

    No es regla productiva.
    """
    lat, lng = result.get("lat"), result.get("lng")
    if lat is None or lng is None or str(result.get("status")) in {"ZERO_RESULTS", "NO_MATCH"}:
        return "MANUAL"

    dist_m: Optional[float] = None
    if golden_lat is not None and golden_lng is not None:
        dist_m = _haversine_m(golden_lat, golden_lng, float(lat), float(lng))
        if dist_m > 100:
            return "MANUAL"
        if dist_m <= 50:
            lt = str(result.get("location_type") or "").upper()
            if result.get("partial_match"):
                return "REVISION"
            if lt in LOCATION_TYPE_HIGH or lt in LOCATION_TYPE_MEDIUM or lt == "BUILDING":
                return "AUTO_BUENO"
            if lt in LOCATION_TYPE_LOW:
                return "REVISION"
            return "AUTO_BUENO"
        return "REVISION"

    lt = str(result.get("location_type") or "").upper()
    if result.get("partial_match"):
        return "REVISION"
    if lt in LOCATION_TYPE_HIGH or lt in LOCATION_TYPE_MEDIUM or lt == "BUILDING":
        return "AUTO_BUENO"
    if lt in LOCATION_TYPE_LOW:
        return "REVISION"
    q = result.get("quality")
    s = result.get("score")
    if q == "building" and s is not None and float(s) >= 0.95:
        return "AUTO_BUENO"
    if lat is not None:
        return "REVISION"
    return "MANUAL"


def _build_numero_queries(dom: Domicilio) -> dict[str, str]:
    """Queries A (raw) y B (normalizada SMT) para NUMERO."""
    calle_raw = (dom.calle or "").strip()
    calle_norm = (dom.calle_normalizada or calle_raw).strip()
    numero = (dom.numero or "").strip()
    return {
        "raw": f"{calle_raw} {numero}, {SMT_SUFFIX}",
        "normalized": f"{calle_norm} {numero}, {SMT_SUFFIX}",
    }


def _build_esquina_queries(dom: Domicilio) -> dict[str, str]:
    """Queries ESQUINA en ambos órdenes."""
    calle = (dom.calle_normalizada or dom.calle or "").strip()
    esquina = (
        dom.esquina_normalizada
        or dom.esquina_raw
        or (dom.numero if dom.numero_tipo == "ESQUINA" else "")
        or ""
    ).strip()
    return {
        "calle_y_esquina": f"{calle} y {esquina}, {SMT_SUFFIX}",
        "esquina_y_calle": f"{esquina} y {calle}, {SMT_SUFFIX}",
    }


def _pick_best_result(
    results: dict[str, dict[str, Any]],
    *,
    golden_lat: Optional[float],
    golden_lng: Optional[float],
) -> tuple[str, dict[str, Any]]:
    """Elige mejor variante de query según distancia al golden o precisión."""
    best_key = ""
    best: dict[str, Any] = {}
    best_score = -1.0

    for key, res in results.items():
        if res.get("lat") is None:
            continue
        score = 0.0
        if golden_lat is not None and golden_lng is not None:
            d = _haversine_m(golden_lat, golden_lng, float(res["lat"]), float(res["lng"]))
            score = max(0.0, 200.0 - d)
        else:
            tier = _precision_tier(res.get("location_type"))
            score = {"alta": 100, "media": 60, "baja": 20, "unknown": 10}.get(tier, 0)
        if score > best_score:
            best_score = score
            best_key = key
            best = res
    return best_key, best


def _fetch_stratum_ids(
    stratum: str,
    limit: int,
    exclude_ids: Optional[set[int]] = None,
) -> list[int]:
    """
    Selecciona domicilio_id por estrato (solo lectura).

    Args:
        stratum: NUMERO | ESQUINA | NORM_PENDING | GEO_PENDING | MANUAL.
        limit: máximo a retornar.
        exclude_ids: ids ya incluidos en otro estrato.

    Returns:
        Lista de domicilio_id.
    """
    exclude_ids = exclude_ids or set()
    exclude_clause = ""
    params: dict[str, Any] = {"lim": int(limit)}
    if exclude_ids:
        placeholders = ", ".join(f":ex{i}" for i in range(len(exclude_ids)))
        exclude_clause = f" AND d.id NOT IN ({placeholders})"
        for i, eid in enumerate(sorted(exclude_ids)):
            params[f"ex{i}"] = int(eid)

    base = f"""
        SELECT d.id
        FROM domicilio d
        LEFT JOIN domicilio_geocode g ON g.domicilio_id = d.id AND g.deleted_at IS NULL
        WHERE d.deleted_at IS NULL
        {exclude_clause}
    """
    order = "ORDER BY d.updated_at DESC, d.id DESC"
    if stratum == "NUMERO":
        sql = base + """
            AND (d.numero_tipo IS NULL OR d.numero_tipo = 'NUMERO')
            AND d.calle_norm_status = 'OK'
            AND (g.geo_status IS NULL OR g.geo_status NOT IN ('NORM_PENDING'))
        """ + order + " LIMIT :lim"
    elif stratum == "ESQUINA":
        sql = base + """
            AND d.numero_tipo = 'ESQUINA'
        """ + order + " LIMIT :lim"
    elif stratum == "NORM_PENDING":
        sql = base + """
            AND g.geo_status = 'NORM_PENDING'
        """ + order + " LIMIT :lim"
    elif stratum == "GEO_PENDING":
        sql = base + """
            AND g.geo_status = 'GEO_PENDING'
            AND (g.provider = 'geoapify' OR g.provider IS NULL)
        """ + order + " LIMIT :lim"
    elif stratum == "MANUAL":
        sql = base + """
            AND g.source = 'MANUAL'
            AND g.geo_status = 'OK'
            AND g.lat IS NOT NULL AND g.lng IS NOT NULL
            ORDER BY
                CASE WHEN d.calle_norm_status = 'OK' THEN 0 ELSE 1 END,
                g.updated_at DESC,
                d.id DESC
            LIMIT :lim
        """
    else:
        return []

    rows = db.session.execute(text(sql), params).fetchall()
    return [int(r[0]) for r in rows]


def _build_dataset(sample_size: int) -> list[dict[str, Any]]:
    """
    Arma dataset estratificado (~100) con prioridades del ticket.

    Returns:
        Lista de registros con metadatos de domicilio + geo existente.
    """
    seen: set[int] = set()
    records: list[dict[str, Any]] = []
    total_target = min(sample_size, sum(STRATUM_TARGETS.values()))

    for stratum, target in STRATUM_TARGETS.items():
        if len(records) >= total_target:
            break
        need = min(target, total_target - len(records))
        ids = _fetch_stratum_ids(stratum, need * 5, exclude_ids=seen)
        added = 0
        for dom_id in ids:
            if added >= need or dom_id in seen:
                continue
            dom = db.session.get(Domicilio, dom_id)
            if not dom:
                continue
            geo = DomicilioGeocode.query.filter_by(domicilio_id=dom_id).first()
            seen.add(dom_id)
            golden_lat = float(geo.lat) if geo and geo.lat is not None else None
            golden_lng = float(geo.lng) if geo and geo.lng is not None else None
            has_golden = (
                stratum == "MANUAL"
                and geo is not None
                and str(geo.source or "") == "MANUAL"
                and str(geo.geo_status or "") == "OK"
                and golden_lat is not None
                and golden_lng is not None
            )
            records.append(
                {
                    "domicilio_id": dom_id,
                    "stratum": stratum,
                    "calle": dom.calle,
                    "numero": dom.numero,
                    "numero_tipo": dom.numero_tipo,
                    "calle_normalizada": dom.calle_normalizada,
                    "calle_norm_status": dom.calle_norm_status,
                    "esquina_normalizada": dom.esquina_normalizada,
                    "esquina_raw": dom.esquina_raw,
                    "existing_geo_status": str(geo.geo_status) if geo else None,
                    "existing_provider": str(geo.provider) if geo and geo.provider else None,
                    "existing_quality": geo.quality if geo else None,
                    "existing_score": float(geo.score) if geo and geo.score is not None else None,
                    "golden_lat": golden_lat if has_golden else None,
                    "golden_lng": golden_lng if has_golden else None,
                    "golden_source": "MANUAL" if has_golden else None,
                }
            )
            added += 1

    if len(records) < total_target:
        extra_ids = _fetch_stratum_ids("NUMERO", (total_target - len(records)) * 2, exclude_ids=seen)
        for dom_id in extra_ids:
            if dom_id in seen or len(records) >= total_target:
                break
            dom = db.session.get(Domicilio, dom_id)
            geo = DomicilioGeocode.query.filter_by(domicilio_id=dom_id).first()
            if not dom:
                continue
            seen.add(dom_id)
            records.append(
                {
                    "domicilio_id": dom_id,
                    "stratum": "NUMERO_FILL",
                    "calle": dom.calle,
                    "numero": dom.numero,
                    "numero_tipo": dom.numero_tipo,
                    "calle_normalizada": dom.calle_normalizada,
                    "calle_norm_status": dom.calle_norm_status,
                    "esquina_normalizada": dom.esquina_normalizada,
                    "esquina_raw": dom.esquina_raw,
                    "existing_geo_status": str(geo.geo_status) if geo else None,
                    "existing_provider": str(geo.provider) if geo and geo.provider else None,
                    "existing_quality": geo.quality if geo else None,
                    "existing_score": float(geo.score) if geo and geo.score is not None else None,
                    "golden_lat": None,
                    "golden_lng": None,
                    "golden_source": None,
                }
            )
    return records[:total_target]


def _evaluate_record(
    rec: dict[str, Any],
    dom: Domicilio,
    google_key: str,
    counters: dict[str, int],
    latencies: dict[str, list[float]],
) -> dict[str, Any]:
    """Evalúa un domicilio contra Google y Geoapify (solo requests externos)."""
    golden_lat = rec.get("golden_lat")
    golden_lng = rec.get("golden_lng")
    out: dict[str, Any] = {
        "domicilio_id": rec["domicilio_id"],
        "stratum": rec["stratum"],
        "calle": rec["calle"],
        "numero": rec["numero"],
        "numero_tipo": rec["numero_tipo"],
        "calle_norm_status": rec["calle_norm_status"],
        "golden_source": rec.get("golden_source"),
        "google_variants": {},
        "geoapify_variants": {},
    }

    is_esquina = str(dom.numero_tipo or "") == "ESQUINA"
    if is_esquina:
        queries = _build_esquina_queries(dom)
    else:
        queries = _build_numero_queries(dom)
        if rec["stratum"] == "NORM_PENDING":
            if dom.calle_normalizada:
                queries["norm_available"] = queries["normalized"]
            queries["norm_pending_raw"] = queries["raw"]

    google_results: dict[str, dict[str, Any]] = {}
    geoapify_results: dict[str, dict[str, Any]] = {}

    for qname, query in queries.items():
        time.sleep(REQUEST_PAUSE_SEC)
        try:
            g_res, g_ms = _request_google(query, google_key)
            counters["google_requests"] += 1
            latencies["google"].append(g_ms)
            google_results[qname] = {**g_res, "latency_ms": round(g_ms, 1)}
        except Exception as exc:  # noqa: BLE001
            google_results[qname] = {
                "provider": "google",
                "status": "ERROR",
                "error": str(exc)[:200],
                "query": query,
            }
            counters["google_errors"] += 1

        time.sleep(REQUEST_PAUSE_SEC)
        try:
            a_res, a_ms = _request_geoapify_timed(query)
            counters["geoapify_requests"] += 1
            latencies["geoapify"].append(a_ms)
            geoapify_results[qname] = {**a_res, "latency_ms": round(a_ms, 1)}
        except Exception as exc:  # noqa: BLE001
            geoapify_results[qname] = {
                "provider": "geoapify",
                "status": "ERROR",
                "error": str(exc)[:200],
                "query": query,
            }
            counters["geoapify_errors"] += 1

    out["google_variants"] = google_results
    out["geoapify_variants"] = geoapify_results

    g_best_key, g_best = _pick_best_result(google_results, golden_lat=golden_lat, golden_lng=golden_lng)
    a_best_key, a_best = _pick_best_result(geoapify_results, golden_lat=golden_lat, golden_lng=golden_lng)
    out["google_best_variant"] = g_best_key
    out["geoapify_best_variant"] = a_best_key
    out["google_best"] = g_best
    out["geoapify_best"] = a_best

    out["google_operational"] = _classify_operational(
        g_best, golden_lat=golden_lat, golden_lng=golden_lng
    )
    out["geoapify_operational"] = _classify_operational(
        a_best, golden_lat=golden_lat, golden_lng=golden_lng
    )

    if golden_lat is not None and golden_lng is not None and g_best.get("lat") is not None:
        out["google_distance_m"] = round(
            _haversine_m(golden_lat, golden_lng, float(g_best["lat"]), float(g_best["lng"])), 1
        )
    if golden_lat is not None and golden_lng is not None and a_best.get("lat") is not None:
        out["geoapify_distance_m"] = round(
            _haversine_m(golden_lat, golden_lng, float(a_best["lat"]), float(a_best["lng"])), 1
        )

    if is_esquina and "calle_y_esquina" in google_results and "esquina_y_calle" in google_results:
        g1 = google_results["calle_y_esquina"]
        g2 = google_results["esquina_y_calle"]
        if g1.get("lat") and g2.get("lat"):
            out["google_esquina_order_distance_m"] = round(
                _haversine_m(float(g1["lat"]), float(g1["lng"]), float(g2["lat"]), float(g2["lng"])), 1
            )
            out["google_esquina_same_intersection"] = out["google_esquina_order_distance_m"] <= 30

    out["google_precision_tier"] = _precision_tier(g_best.get("location_type"))
    out["google_place_id"] = g_best.get("place_id")

    return out


def _operational_pct(rows: list[dict[str, Any]], provider_key: str, stratum: Optional[str] = None) -> dict[str, float]:
    subset = [r for r in rows if stratum is None or r.get("stratum") == stratum]
    if not subset:
        return {}
    n = len(subset)
    counts = {"AUTO_BUENO": 0, "REVISION": 0, "MANUAL": 0}
    for r in subset:
        op = str(r.get(provider_key) or "MANUAL")
        counts[op] = counts.get(op, 0) + 1
    return {k: round(100 * v / n, 1) for k, v in counts.items()}


def _aggregate_report(
    evaluated: list[dict[str, Any]],
    counters: dict[str, int],
    latencies: dict[str, list[float]],
) -> dict[str, Any]:
    """Arma reporte agregado del PoC."""
    manual_rows = [r for r in evaluated if r.get("golden_source") == "MANUAL"]
    norm_pending_rows = [r for r in evaluated if r.get("stratum") == "NORM_PENDING"]
    numero_rows = [r for r in evaluated if r.get("stratum") in ("NUMERO", "NUMERO_FILL")]
    esquina_rows = [r for r in evaluated if r.get("stratum") == "ESQUINA"]

    google_dists = [r["google_distance_m"] for r in evaluated if r.get("google_distance_m") is not None]
    geoapify_dists = [r["geoapify_distance_m"] for r in evaluated if r.get("geoapify_distance_m") is not None]

    google_resolved_norm = sum(
        1
        for r in norm_pending_rows
        if r.get("google_operational") in ("AUTO_BUENO", "REVISION")
        and r.get("google_best", {}).get("lat") is not None
    )
    manual_google_would_fix = sum(
        1 for r in manual_rows if r.get("google_operational") == "AUTO_BUENO"
    )

    examples: list[dict[str, Any]] = []
    for r in evaluated:
        g_op = r.get("google_operational")
        a_op = r.get("geoapify_operational")
        if g_op == "AUTO_BUENO" and a_op != "AUTO_BUENO":
            examples.append(
                {
                    "type": "google_wins",
                    "domicilio_id": r["domicilio_id"],
                    "stratum": r["stratum"],
                    "calle": r["calle"],
                    "numero": r["numero"],
                    "google": r.get("google_best"),
                    "geoapify": r.get("geoapify_best"),
                }
            )
        elif a_op == "AUTO_BUENO" and g_op != "AUTO_BUENO":
            examples.append(
                {
                    "type": "geoapify_wins",
                    "domicilio_id": r["domicilio_id"],
                    "stratum": r["stratum"],
                    "calle": r["calle"],
                    "numero": r["numero"],
                    "google": r.get("google_best"),
                    "geoapify": r.get("geoapify_best"),
                }
            )
    examples = examples[:20]

    stratum_counts: dict[str, int] = {}
    for r in evaluated:
        s = str(r.get("stratum") or "unknown")
        stratum_counts[s] = stratum_counts.get(s, 0) + 1

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ticket": "GEO-GOOGLE.1",
            "total_evaluated": len(evaluated),
            "stratum_counts": stratum_counts,
        },
        "requests": {
            "google_total": counters.get("google_requests", 0),
            "geoapify_total": counters.get("geoapify_requests", 0),
            "google_errors": counters.get("google_errors", 0),
            "geoapify_errors": counters.get("geoapify_errors", 0),
        },
        "operational": {
            "google_all": _operational_pct(evaluated, "google_operational"),
            "geoapify_all": _operational_pct(evaluated, "geoapify_operational"),
            "google_numero": _operational_pct(evaluated, "google_operational", "NUMERO"),
            "geoapify_numero": _operational_pct(evaluated, "geoapify_operational", "NUMERO"),
            "google_esquina": _operational_pct(evaluated, "google_operational", "ESQUINA"),
            "geoapify_esquina": _operational_pct(evaluated, "geoapify_operational", "ESQUINA"),
        },
        "norm_pending": {
            "sampled": len(norm_pending_rows),
            "google_resolved": google_resolved_norm,
            "google_resolved_pct": round(100 * google_resolved_norm / len(norm_pending_rows), 1)
            if norm_pending_rows
            else None,
        },
        "manual_golden": {
            "sampled": len(manual_rows),
            "google_would_have_avoided_manual": manual_google_would_fix,
            "pct": round(100 * manual_google_would_fix / len(manual_rows), 1) if manual_rows else None,
        },
        "distance_vs_golden": {
            "google": _distance_buckets(google_dists),
            "geoapify": _distance_buckets(geoapify_dists),
        },
        "latency_ms": {
            "google": _latency_stats(latencies.get("google", [])),
            "geoapify": _latency_stats(latencies.get("geoapify", [])),
        },
        "location_type_google": _count_location_types(evaluated, "google_best"),
        "place_id_available_google": sum(
            1 for r in evaluated if r.get("google_best", {}).get("place_id")
        ),
        "examples": examples,
        "recommendation": _recommendation(evaluated),
        "records": evaluated,
    }


def _count_location_types(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in rows:
        lt = str((r.get(key) or {}).get("location_type") or "NONE")
        counts[lt] = counts.get(lt, 0) + 1
    return counts


def _recommendation(evaluated: list[dict[str, Any]]) -> dict[str, Any]:
    """Criterio orientativo de decisión (no migración automática)."""
    g = _operational_pct(evaluated, "google_operational")
    a = _operational_pct(evaluated, "geoapify_operational")
    g_auto = g.get("AUTO_BUENO", 0)
    a_auto = a.get("AUTO_BUENO", 0)
    delta = g_auto - a_auto
    if delta >= 40:
        verdict = "FUERTE_CANDIDATO"
        note = f"Google AUTO_BUENO {g_auto}% vs Geoapify {a_auto}% — diferencia suficiente para fase siguiente."
    elif delta >= 15:
        verdict = "EVALUAR_MAS"
        note = f"Diferencia moderada ({delta:.1f}pp). Ampliar muestra antes de decidir."
    else:
        verdict = "NO_MIGRAR_TODAVIA"
        note = f"Diferencia pequeña ({delta:.1f}pp). No justifica migración por benchmark actual."
    return {
        "verdict": verdict,
        "google_auto_bueno_pct": g_auto,
        "geoapify_auto_bueno_pct": a_auto,
        "delta_pp": round(delta, 1),
        "note": note,
    }


def _write_csv(path: Path, evaluated: list[dict[str, Any]]) -> None:
    """Exporta filas resumidas a CSV diagnóstico."""
    fieldnames = [
        "domicilio_id",
        "stratum",
        "calle",
        "numero",
        "numero_tipo",
        "calle_norm_status",
        "golden_source",
        "google_operational",
        "geoapify_operational",
        "google_best_variant",
        "geoapify_best_variant",
        "google_location_type",
        "google_place_id",
        "google_distance_m",
        "geoapify_distance_m",
        "google_lat",
        "google_lng",
        "geoapify_lat",
        "geoapify_lng",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in evaluated:
            gb = r.get("google_best") or {}
            ab = r.get("geoapify_best") or {}
            writer.writerow(
                {
                    **{k: r.get(k) for k in fieldnames},
                    "google_location_type": gb.get("location_type"),
                    "google_place_id": gb.get("place_id"),
                    "google_lat": gb.get("lat"),
                    "google_lng": gb.get("lng"),
                    "geoapify_lat": ab.get("lat"),
                    "geoapify_lng": ab.get("lng"),
                }
            )


def _print_summary(report: dict[str, Any]) -> None:
    """Imprime resumen legible en consola."""
    m = report["meta"]
    op = report["operational"]
    print("\n=== GEO-GOOGLE.1 PoC REPORT ===")
    print(f"Total evaluados: {m['total_evaluated']}")
    print(f"Estratos: {json.dumps(m['stratum_counts'], ensure_ascii=False)}")
    print(f"Requests Google: {report['requests']['google_total']}")
    print(f"Requests Geoapify: {report['requests']['geoapify_total']}")

    print("\n--- NUMERO (AUTO_BUENO %) ---")
    print(f"  Google:   {op.get('google_numero', {})}")
    print(f"  Geoapify: {op.get('geoapify_numero', {})}")

    print("\n--- ESQUINA (AUTO_BUENO %) ---")
    print(f"  Google:   {op.get('google_esquina', {})}")
    print(f"  Geoapify: {op.get('geoapify_esquina', {})}")

    print("\n--- TODOS ---")
    print(f"  Google:   {op.get('google_all', {})}")
    print(f"  Geoapify: {op.get('geoapify_all', {})}")

    np = report["norm_pending"]
    print(f"\nNORM_PENDING Google resolvió: {np['google_resolved']}/{np['sampled']}")

    mg = report["manual_golden"]
    print(f"MANUAL Google habría evitado: {mg['google_would_have_avoided_manual']}/{mg['sampled']}")

    print("\n--- Distancia al golden ---")
    print(f"  Google:   {report['distance_vs_golden']['google']}")
    print(f"  Geoapify: {report['distance_vs_golden']['geoapify']}")

    print("\n--- Latencia (ms) ---")
    print(f"  Google:   {report['latency_ms']['google']}")
    print(f"  Geoapify: {report['latency_ms']['geoapify']}")

    print(f"\nplace_id Google disponible: {report['place_id_available_google']}/{m['total_evaluated']}")
    print(f"location_type Google: {report['location_type_google']}")

    rec = report["recommendation"]
    print(f"\nRecomendación: {rec['verdict']} — {rec['note']}")

    if report.get("examples"):
        print(f"\nEjemplos representativos ({len(report['examples'])}):")
        for ex in report["examples"][:10]:
            print(f"  [{ex['type']}] dom={ex['domicilio_id']} {ex['calle']} {ex['numero']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="GEO-GOOGLE.1 PoC benchmark")
    parser.add_argument("--sample-size", type=int, default=100, help="Tamaño objetivo del dataset")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="scripts/output",
        help="Directorio para JSON/CSV diagnóstico",
    )
    parser.add_argument("--dry-run", action="store_true", help="Solo arma dataset, sin llamar APIs")
    args = parser.parse_args()

    google_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_GEOCODING_API_KEY")
    geoapify_key = os.getenv("GEOAPIFY_API_KEY")

    if not args.dry_run and not google_key:
        print("ERROR: GOOGLE_MAPS_API_KEY no configurada en .env")
        sys.exit(1)
    if not args.dry_run and not geoapify_key:
        print("ERROR: GEOAPIFY_API_KEY no configurada (necesaria para comparación)")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        print("GEO-GOOGLE.1 — seleccionando dataset...")
        dataset = _build_dataset(args.sample_size)
        print(f"Dataset: {len(dataset)} domicilios")
        for s, n in STRATUM_TARGETS.items():
            have = sum(1 for d in dataset if d["stratum"] == s)
            print(f"  {s}: {have}/{n}")

        if args.dry_run:
            print(json.dumps({"dataset": dataset, "dry_run": True}, indent=2, ensure_ascii=False))
            return

        counters: dict[str, int] = {
            "google_requests": 0,
            "geoapify_requests": 0,
            "google_errors": 0,
            "geoapify_errors": 0,
        }
        latencies: dict[str, list[float]] = {"google": [], "geoapify": []}
        evaluated: list[dict[str, Any]] = []

        for i, rec in enumerate(dataset, 1):
            dom = db.session.get(Domicilio, int(rec["domicilio_id"]))
            if not dom:
                continue
            print(f"[{i}/{len(dataset)}] dom={rec['domicilio_id']} stratum={rec['stratum']} {rec['calle']}")
            row = _evaluate_record(rec, dom, google_key, counters, latencies)
            evaluated.append(row)

        report = _aggregate_report(evaluated, counters, latencies)

        out_dir = Path(args.output_dir)
        if not out_dir.is_absolute():
            out_dir = ROOT / out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = out_dir / f"diag_geo_google_1_{ts}.json"
        csv_path = out_dir / f"diag_geo_google_1_{ts}.csv"

        summary_copy = {k: v for k, v in report.items() if k != "records"}
        json_path.write_text(json.dumps(summary_copy, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        json_path_full = out_dir / f"diag_geo_google_1_{ts}_full.json"
        json_path_full.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        _write_csv(csv_path, evaluated)

        print(f"\nJSON resumen: {json_path}")
        print(f"JSON completo: {json_path_full}")
        print(f"CSV: {csv_path}")
        _print_summary(report)


if __name__ == "__main__":
    main()
