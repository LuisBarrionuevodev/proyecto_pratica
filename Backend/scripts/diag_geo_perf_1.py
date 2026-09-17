"""
GEO-PERF.1 — medición HTTP commit-batch antes/después del geocode async.

Compara:
- legacy_sync: create + pipeline_post_commit bloqueante por fila (comportamiento previo)
- async_enqueue: create + prepare/encolar sin esperar proveedor (comportamiento nuevo)

Uso:
    cd Backend
    python scripts/diag_geo_perf_1.py
    python scripts/diag_geo_perf_1.py --rows 20
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.database import db
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service import (
    enqueue_geocode_post_commit,
    prepare_geocode_state_after_commit,
)
from app.domains.geolocalizacion.geocode.services.pipeline_service import pipeline_post_commit
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from tests.relevamiento_test_helpers import get_or_create_test_relevador, get_test_rubro, uniq


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
        return {"n": 0, "p50": 0, "p95": 0, "max": 0, "mean": 0, "total": 0}
    return {
        "n": len(values),
        "p50": round(_percentile(values, 50), 1),
        "p95": round(_percentile(values, 95), 1),
        "max": round(max(values), 1),
        "mean": round(statistics.mean(values), 1),
        "total": round(sum(values), 1),
    }


def _mk_payload(calle: str, numero: str) -> dict:
    rev = get_or_create_test_relevador()
    rub = get_test_rubro()
    return {
        "fecha": date.today().isoformat(),
        "relevadores_nombres": [rev.nombre],
        "domicilio": {"calle": calle, "numero": numero},
        "rubro_nombre": rub.nombre,
    }


def measure_legacy_sync(n_rows: int) -> dict:
    """Simula commit-batch previo: pipeline_post_commit bloqueante por fila."""
    per_row: list[float] = []
    domicilio_ids: list[int] = []

    t0 = time.perf_counter()
    for i in range(n_rows):
        t_row = time.perf_counter()
        rel = crear_relevamiento_desde_payload(
            _mk_payload(uniq(f"DiagLegacy{i}"), str(1000 + i))
        )
        pipeline_post_commit(int(rel.domicilio_id))
        per_row.append((time.perf_counter() - t_row) * 1000.0)
        domicilio_ids.append(int(rel.domicilio_id))

    total_ms = (time.perf_counter() - t0) * 1000.0
    db.session.rollback()
    return {
        "mode": "legacy_sync",
        "rows": n_rows,
        "total_ms": round(total_ms, 1),
        "per_row_ms": _stats(per_row),
        "note": "create + pipeline_post_commit síncrono (incluye proveedor si aplica)",
    }


def measure_async_enqueue(n_rows: int) -> dict:
    """Simula commit-batch nuevo: persistir + marcar geo pendiente + encolar."""
    per_row: list[float] = []
    domicilio_ids: list[int] = []

    t0 = time.perf_counter()
    for i in range(n_rows):
        t_row = time.perf_counter()
        rel = crear_relevamiento_desde_payload(
            _mk_payload(uniq(f"DiagAsync{i}"), str(2000 + i))
        )
        dom_id = int(rel.domicilio_id)
        prepare_geocode_state_after_commit(dom_id)
        domicilio_ids.append(dom_id)
        per_row.append((time.perf_counter() - t_row) * 1000.0)

    t_enqueue = time.perf_counter()
    enqueue_geocode_post_commit(domicilio_ids)
    enqueue_ms = (time.perf_counter() - t_enqueue) * 1000.0
    total_ms = (time.perf_counter() - t0) * 1000.0
    db.session.rollback()
    return {
        "mode": "async_enqueue",
        "rows": n_rows,
        "total_ms": round(total_ms, 1),
        "enqueue_batch_ms": round(enqueue_ms, 1),
        "per_row_ms": _stats(per_row),
        "note": "create + prepare_geocode_state; encolar al final del lote (sin proveedor)",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rows",
        type=int,
        nargs="+",
        default=[1, 5, 10, 20],
        help="Tamaños de lote a medir",
    )
    args = parser.parse_args()

    app = create_app()
    results: dict[str, list[dict]] = {"legacy_sync": [], "async_enqueue": []}

    with app.app_context():
        print("=== GEO-PERF.1 MEDICIÓN ===\n")
        for n in args.rows:
            print(f"--- N={n} legacy_sync ---")
            legacy = measure_legacy_sync(n)
            print(json.dumps(legacy, indent=2, ensure_ascii=False))
            results["legacy_sync"].append(legacy)

            print(f"\n--- N={n} async_enqueue ---")
            async_res = measure_async_enqueue(n)
            print(json.dumps(async_res, indent=2, ensure_ascii=False))
            results["async_enqueue"].append(async_res)

            if legacy["total_ms"] > 0:
                speedup = round(legacy["total_ms"] / max(async_res["total_ms"], 0.1), 2)
                print(f"\nSpeedup total N={n}: {speedup}x\n")

        print("\n=== RESUMEN COMPARATIVO ===")
        summary = []
        for legacy, async_res in zip(results["legacy_sync"], results["async_enqueue"]):
            summary.append(
                {
                    "rows": legacy["rows"],
                    "legacy_total_ms": legacy["total_ms"],
                    "async_total_ms": async_res["total_ms"],
                    "legacy_per_row_p50_ms": legacy["per_row_ms"]["p50"],
                    "async_per_row_p50_ms": async_res["per_row_ms"]["p50"],
                    "speedup_total": round(
                        legacy["total_ms"] / max(async_res["total_ms"], 0.1), 2
                    ),
                }
            )
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
