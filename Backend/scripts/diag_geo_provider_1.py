"""
GEO-PROVIDER.1 — diagnóstico: pipeline, tiempos y benchmark Geoapify vs Google (PoC aislado).

Uso:
    cd Backend
    python scripts/diag_geo_provider_1.py
    python scripts/diag_geo_provider_1.py --sample 50
    python scripts/diag_geo_provider_1.py --benchmark-only
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.database import db
from app.domains.geolocalizacion.geocode.services.distritos_service import resolve_distrito_id
from app.domains.geolocalizacion.geocode.services.pipeline_service import pipeline_post_commit
from app.domains.geolocalizacion.geocoding.services.geocode_service import (
    _build_query,
    _evaluate_geoapify,
    _request_geoapify,
)
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    compute_addr_hash,
    on_domicilio_changed,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio,
)
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.models import Domicilio, DomicilioGeocode
from tests.relevamiento_test_helpers import get_or_create_test_relevador, get_test_rubro, uniq


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
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


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"n": 0, "p50": 0, "p95": 0, "max": 0, "mean": 0}
    return {
        "n": len(values),
        "p50": round(_percentile(values, 50), 1),
        "p95": round(_percentile(values, 95), 1),
        "max": round(max(values), 1),
        "mean": round(statistics.mean(values), 1),
    }


def _request_google_geocode(query: str, api_key: str) -> tuple[dict[str, Any], float]:
    params = {
        "address": query,
        "key": api_key,
        "region": "ar",
        "components": "country:AR|administrative_area:Tucumán|locality:San Miguel de Tucumán",
    }
    url = "https://maps.googleapis.com/maps/api/geocode/json?" + urllib.parse.urlencode(params)
    t0 = time.perf_counter()
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    ms = (time.perf_counter() - t0) * 1000.0
    return data, ms


def _google_best_result(data: dict[str, Any]) -> dict[str, Any] | None:
    results = data.get("results") or []
    if not results:
        return None
    r0 = results[0]
    loc = (r0.get("geometry") or {}).get("location") or {}
    return {
        "lat": loc.get("lat"),
        "lng": loc.get("lng"),
        "formatted_address": r0.get("formatted_address"),
        "location_type": (r0.get("geometry") or {}).get("location_type"),
        "place_id": r0.get("place_id"),
        "status": data.get("status"),
    }


def _measure_pipeline_new_domicilio() -> dict[str, Any]:
    """Mide etapas de crear relevamiento + pipeline_post_commit (rollback al final)."""
    rev = get_or_create_test_relevador()
    rub = get_test_rubro()
    calle = uniq("DiagGeo1")
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    payload = {
        "fecha": "2026-06-15",
        "relevadores_nombres": [rev.nombre],
        "domicilio": {"calle": calle, "numero": "1500"},
        "rubro_nombre": rub.nombre,
    }
    t1 = time.perf_counter()
    rel = crear_relevamiento_desde_payload(payload)
    t2 = time.perf_counter()
    dom_id = int(rel.domicilio_id)

    t3 = time.perf_counter()
    norm = normalizar_domicilio(dom_id)
    t4 = time.perf_counter()
    geo = on_domicilio_changed(dom_id)
    t5 = time.perf_counter()

    dom = db.session.get(Domicilio, dom_id)
    geo_row = DomicilioGeocode.query.filter_by(domicilio_id=dom_id).first()
    dist_ms = 0.0
    if geo_row and geo_row.lat and geo_row.lng and geo_row.geo_status == "OK":
        td0 = time.perf_counter()
        resolve_distrito_id(float(geo_row.lat), float(geo_row.lng))
        dist_ms = (time.perf_counter() - td0) * 1000.0

    timings["validation_create_ms"] = round((t2 - t1) * 1000, 1)
    timings["normalizacion_ms"] = round((t4 - t3) * 1000, 1)
    timings["geocode_orchestrator_ms"] = round((t5 - t4) * 1000, 1)
    timings["distrito_resolve_ms"] = round(dist_ms, 1)
    timings["total_pipeline_post_commit_ms"] = round((t5 - t3) * 1000, 1)
    timings["total_create_plus_post_ms"] = round((t5 - t0) * 1000, 1)

    result = {
        "domicilio_id": dom_id,
        "geo_status": getattr(geo_row, "geo_status", None),
        "cached": geo.get("cached") if isinstance(geo, dict) else None,
        "skipped": geo.get("skipped") if isinstance(geo, dict) else None,
        "norm": norm,
        "timings_ms": timings,
    }
    db.session.rollback()
    return result


def _measure_batch_simulation(n_rows: int) -> dict[str, Any]:
    """Simula commit-batch secuencial de N filas con direcciones únicas."""
    rev = get_or_create_test_relevador()
    rub = get_test_rubro()
    per_row: list[float] = []
    provider_ms: list[float] = []
    cached_rows = 0

    t_batch0 = time.perf_counter()
    for i in range(n_rows):
        calle = uniq(f"DiagBatch{i}")
        t0 = time.perf_counter()
        rel = crear_relevamiento_desde_payload(
            {
                "fecha": "2026-06-15",
                "relevadores_nombres": [rev.nombre],
                "domicilio": {"calle": calle, "numero": str(1000 + i)},
                "rubro_nombre": rub.nombre,
            }
        )
        pipeline_post_commit(int(rel.domicilio_id))
        per_row.append((time.perf_counter() - t0) * 1000.0)
        geo = DomicilioGeocode.query.filter_by(domicilio_id=rel.domicilio_id).first()
        if geo and geo.geo_status == "OK" and geo.provider == "geoapify":
            provider_ms.append(0)  # included in row time

    total_ms = (time.perf_counter() - t_batch0) * 1000.0
    db.session.rollback()
    return {
        "rows": n_rows,
        "total_ms": round(total_ms, 1),
        "per_row_ms": _stats(per_row),
        "sequential": True,
        "note": "Cada fila incluye create+commit+pipeline_post_commit síncrono",
    }


def _sample_addresses(limit: int) -> list[dict[str, Any]]:
    rows = (
        db.session.query(
            Domicilio.id,
            Domicilio.calle,
            Domicilio.numero,
            Domicilio.numero_tipo,
            Domicilio.calle_normalizada,
            Domicilio.esquina_normalizada,
            Domicilio.esquina_raw,
            DomicilioGeocode.lat,
            DomicilioGeocode.lng,
            DomicilioGeocode.geo_status,
            DomicilioGeocode.source,
            DomicilioGeocode.score,
            DomicilioGeocode.quality,
        )
        .join(DomicilioGeocode, Domicilio.id == DomicilioGeocode.domicilio_id)
        .filter(
            Domicilio.deleted_at.is_(None),
            DomicilioGeocode.deleted_at.is_(None),
            Domicilio.calle_norm_status == "OK",
        )
        .order_by(Domicilio.id.desc())
        .limit(limit)
        .all()
    )
    out = []
    for r in rows:
        dom = db.session.get(Domicilio, int(r.id))
        query_norm = _build_query(dom) if dom else None
        query_raw = None
        if dom:
            calle = dom.calle or ""
            if dom.numero_tipo == "ESQUINA":
                esq = dom.esquina_raw or dom.esquina_normalizada or dom.numero
                query_raw = f"{calle} y {esq}, San Miguel de Tucumán, Tucumán, Argentina"
            else:
                query_raw = f"{calle} {dom.numero}, San Miguel de Tucumán, Tucumán, Argentina"
        out.append(
            {
                "domicilio_id": int(r.id),
                "numero_tipo": r.numero_tipo,
                "geo_status": str(r.geo_status),
                "source": str(r.source),
                "score": float(r.score) if r.score is not None else None,
                "quality": r.quality,
                "gold_lat": float(r.lat) if r.lat is not None else None,
                "gold_lng": float(r.lng) if r.lng is not None else None,
                "gold_is_manual": str(r.source) == "MANUAL" and str(r.geo_status) == "OK",
                "query_normalized": query_norm,
                "query_raw": query_raw,
            }
        )
    return out


def _benchmark_providers(samples: list[dict[str, Any]], google_key: str | None) -> dict[str, Any]:
    geoapify_lat: list[float] = []
    google_lat: list[float] = []
    dist_geoapify_norm: list[float] = []
    dist_geoapify_raw: list[float] = []
    dist_google_norm: list[float] = []
    dist_google_raw: list[float] = []
    geoapify_errors = 0
    google_errors = 0
    corner_cases: list[dict[str, Any]] = []

    for s in samples:
        gold_lat, gold_lng = s.get("gold_lat"), s.get("gold_lng")
        has_gold = (
            s.get("gold_is_manual")
            and gold_lat is not None
            and gold_lng is not None
        )

        for qkey in ("query_normalized", "query_raw"):
            query = s.get(qkey)
            if not query:
                continue
            try:
                t0 = time.perf_counter()
                resp = _request_geoapify(query)
                g_ms = (time.perf_counter() - t0) * 1000.0
                geoapify_lat.append(g_ms)
                features = resp.get("features") or []
                if features:
                    ev = _evaluate_geoapify(features[0])
                    lat, lng = ev.get("lat"), ev.get("lng")
                    if has_gold and lat is not None and lng is not None:
                        d = _haversine_m(gold_lat, gold_lng, float(lat), float(lng))
                        if qkey == "query_normalized":
                            dist_geoapify_norm.append(d)
                        else:
                            dist_geoapify_raw.append(d)
            except Exception:
                geoapify_errors += 1

            if google_key:
                try:
                    data, g_ms = _request_google_geocode(query, google_key)
                    google_lat.append(g_ms)
                    best = _google_best_result(data)
                    if has_gold and best and best.get("lat") is not None:
                        d = _haversine_m(
                            gold_lat,
                            gold_lng,
                            float(best["lat"]),
                            float(best["lng"]),
                        )
                        if qkey == "query_normalized":
                            dist_google_norm.append(d)
                        else:
                            dist_google_raw.append(d)
                except Exception:
                    google_errors += 1

    for corners in [
        "San Martín y Maipú, San Miguel de Tucumán, Tucumán, Argentina",
        "Maipú y San Martín, San Miguel de Tucumán, Tucumán, Argentina",
    ]:
        entry: dict[str, Any] = {"query": corners}
        try:
            t0 = time.perf_counter()
            resp = _request_geoapify(corners)
            entry["geoapify_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            feats = resp.get("features") or []
            if feats:
                ev = _evaluate_geoapify(feats[0])
                entry["geoapify_lat"] = ev.get("lat")
                entry["geoapify_lng"] = ev.get("lng")
                entry["geoapify_score"] = ev.get("score")
        except Exception as exc:
            entry["geoapify_error"] = str(exc)
        if google_key:
            try:
                data, ms = _request_google_geocode(corners, google_key)
                entry["google_ms"] = round(ms, 1)
                entry["google"] = _google_best_result(data)
            except Exception as exc:
                entry["google_error"] = str(exc)
        if entry.get("geoapify_lat") and entry.get("google", {}).get("lat"):
            entry["geoapify_vs_google_m"] = round(
                _haversine_m(
                    float(entry["geoapify_lat"]),
                    float(entry["geoapify_lng"]),
                    float(entry["google"]["lat"]),
                    float(entry["google"]["lng"]),
                ),
                1,
            )
        corner_cases.append(entry)

    def _bucket(distances: list[float]) -> dict[str, float]:
        if not distances:
            return {}
        n = len(distances)
        return {
            "n": n,
            "pct_20m": round(100 * sum(1 for d in distances if d <= 20) / n, 1),
            "pct_50m": round(100 * sum(1 for d in distances if d <= 50) / n, 1),
            "pct_100m": round(100 * sum(1 for d in distances if d <= 100) / n, 1),
            "pct_incorrect_100m": round(100 * sum(1 for d in distances if d > 100) / n, 1),
            "median_m": round(statistics.median(distances), 1),
        }

    manual_gold = [s for s in samples if s.get("gold_is_manual")]
    return {
        "samples": len(samples),
        "manual_gold_reference": len(manual_gold),
        "geoapify_latency_ms": _stats(geoapify_lat),
        "google_latency_ms": _stats(google_lat) if google_key else {"skipped": True},
        "geoapify_errors": geoapify_errors,
        "google_errors": google_errors,
        "distance_vs_manual_gold": {
            "geoapify_query_normalized": _bucket(dist_geoapify_norm),
            "geoapify_query_raw": _bucket(dist_geoapify_raw),
            "google_query_normalized": _bucket(dist_google_norm) if google_key else {},
            "google_query_raw": _bucket(dist_google_raw) if google_key else {},
        },
        "corner_cases": corner_cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=30, help="Direcciones para benchmark")
    parser.add_argument("--benchmark-only", action="store_true")
    parser.add_argument("--skip-batch", action="store_true")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        print("=== GEO-PROVIDER.1 DIAGNÓSTICO ===\n")

        geoapify_key = bool(os.getenv("GEOAPIFY_API_KEY"))
        google_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_GEOCODING_API_KEY")
        print(f"GEOAPIFY_API_KEY configurada: {geoapify_key}")
        print(f"GOOGLE API key configurada: {bool(google_key)}")
        print(f"GEOCODER_PROVIDER: {os.getenv('GEOCODER_PROVIDER', os.getenv('GEO_PROVIDER', 'nominatim'))}")

        if not args.benchmark_only:
            print("\n--- Pipeline nuevo domicilio (1 fila) ---")
            single = _measure_pipeline_new_domicilio()
            print(json.dumps(single, indent=2, ensure_ascii=False))

            if not args.skip_batch:
                print("\n--- Simulación batch secuencial ---")
                for n in (1, 5, 10):
                    batch = _measure_batch_simulation(n)
                    print(f"N={n}: {json.dumps(batch, ensure_ascii=False)}")

        if geoapify_key:
            print("\n--- Benchmark proveedores ---")
            samples = _sample_addresses(args.sample)
            bench = _benchmark_providers(samples, google_key)
            print(json.dumps(bench, indent=2, ensure_ascii=False))
        else:
            print("\nBenchmark omitido: falta GEOAPIFY_API_KEY")


if __name__ == "__main__":
    main()
