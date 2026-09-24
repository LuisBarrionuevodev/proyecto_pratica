"""
GEO-PERF.1.2 — diagnóstico: relevamientos guardan pero no geolocalizan.

Uso:
    cd Backend
    python scripts/diag_geo_perf_1_2.py
    python scripts/diag_geo_perf_1_2.py --run-cli
    python scripts/diag_geo_perf_1_2.py --create-batch 5
"""
from __future__ import annotations

import argparse
import json
import os
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
    domicilio_necesita_geocode_post_commit,
    enqueue_geocode_post_commit,
    process_geocode_post_commit_jobs,
)
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_worker import (
    _executor,
    _is_werkzeug_reloader_parent,
    geocode_post_commit_async_enabled,
    init_geocode_post_commit_worker,
    schedule_geocode_post_commit_drain,
)
from app.domains.geolocalizacion.geocode.services.pipeline_service import pipeline_post_commit
from app.domains.geolocalizacion.geocoding.services.geocode_service import _build_query
from app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service import match_calle
from app.domains.grid.services.post_commit_geocode import schedule_geocode_after_grid_commit
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.models import Domicilio, DomicilioGeocode, GeocodePostCommitJob, Relevamiento
from tests.relevamiento_test_helpers import get_or_create_test_relevador, get_test_rubro, uniq


def _geo_snapshot(domicilio_id: int) -> dict:
    dom = db.session.get(Domicilio, int(domicilio_id))
    geo = DomicilioGeocode.query.filter_by(domicilio_id=int(domicilio_id)).first()
    if not dom:
        return {"error": "domicilio no encontrado"}
    match = match_calle(dom.calle or "")
    return {
        "domicilio_id": int(domicilio_id),
        "calle": dom.calle,
        "numero": dom.numero,
        "numero_tipo": dom.numero_tipo,
        "calle_normalizada": dom.calle_normalizada,
        "esquina_normalizada": dom.esquina_normalizada,
        "calle_norm_status": dom.calle_norm_status,
        "esquina_norm_status": dom.esquina_norm_status,
        "match_calle_status": match.get("status"),
        "match_calle_score": match.get("score"),
        "match_calle_canon": match.get("canon"),
        "geo_status": getattr(geo, "geo_status", None),
        "lat": float(geo.lat) if geo and geo.lat is not None else None,
        "lng": float(geo.lng) if geo and geo.lng is not None else None,
        "provider": getattr(geo, "provider", None),
        "quality": getattr(geo, "quality", None),
        "score": float(geo.score) if geo and geo.score is not None else None,
        "error_msg": getattr(geo, "error_msg", None),
        "query": _build_query(dom) if dom.calle_norm_status == "OK" else None,
        "necesita_geocode": domicilio_necesita_geocode_post_commit(int(domicilio_id)),
    }


def _job_snapshot(domicilio_id: int) -> list[dict]:
    rows = (
        GeocodePostCommitJob.query.filter_by(domicilio_id=int(domicilio_id))
        .order_by(GeocodePostCommitJob.id.desc())
        .all()
    )
    out = []
    for j in rows:
        out.append(
            {
                "job_id": j.id,
                "status": str(j.status),
                "attempts": int(j.attempts or 0),
                "last_error": j.last_error,
                "processing_started_at": j.processing_started_at.isoformat() if j.processing_started_at else None,
                "claimed_addr_hash": j.claimed_addr_hash,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
            }
        )
    return out


def _trace_pipeline(domicilio_id: int) -> dict:
    from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
        normalizar_domicilio,
    )
    from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
        is_ready_for_geocode,
        on_domicilio_changed,
    )

    trace: dict = {"domicilio_id": int(domicilio_id), "steps": []}
    dom = db.session.get(Domicilio, int(domicilio_id))
    if not dom:
        trace["stop"] = "domicilio no encontrado"
        return trace

    try:
        norm = normalizar_domicilio(int(domicilio_id))
        trace["steps"].append({"fn": "normalizar_domicilio", "result": norm})
    except Exception as exc:  # noqa: BLE001
        trace["stop"] = f"normalizar_domicilio exception: {exc}"
        return trace

    dom = db.session.get(Domicilio, int(domicilio_id))
    if dom.calle_norm_status != "OK":
        trace["stop"] = f"calle_norm_status={dom.calle_norm_status} → Geoapify no se llama"
        return trace

    if not is_ready_for_geocode(dom):
        trace["stop"] = "is_ready_for_geocode=False después de normalizar"
        return trace

    try:
        geo = on_domicilio_changed(int(domicilio_id))
        trace["steps"].append({"fn": "on_domicilio_changed", "result": geo})
    except Exception as exc:  # noqa: BLE001
        trace["stop"] = f"on_domicilio_changed exception: {exc}"
        return trace

    snap = _geo_snapshot(int(domicilio_id))
    trace["final_geo"] = snap
    trace["stop"] = f"geo_status={snap.get('geo_status')}"
    return trace


def _env_report() -> dict:
    keys = [
        "GEO_POST_COMMIT_ASYNC",
        "GEO_POST_COMMIT_WORKER_THREADS",
        "GEO_POST_COMMIT_DRAIN_LIMIT",
        "GEO_POST_COMMIT_MAX_ATTEMPTS",
        "GEO_POST_COMMIT_PROCESSING_LEASE_SEC",
        "FLASK_DEBUG",
        "FLASK_ENV",
        "WERKZEUG_RUN_MAIN",
        "GEOCODER_PROVIDER",
        "GEO_PROVIDER",
        "GEOAPIFY_API_KEY",
    ]
    return {k: ("SET" if k == "GEOAPIFY_API_KEY" and os.getenv(k) else os.getenv(k)) for k in keys}


def _worker_report(app) -> dict:
    return {
        "async_enabled": geocode_post_commit_async_enabled(),
        "is_werkzeug_reloader_parent": _is_werkzeug_reloader_parent(),
        "executor_after_init": _executor is not None,
        "would_skip_init": (
            not geocode_post_commit_async_enabled() or _is_werkzeug_reloader_parent()
        ),
    }


def _queue_counts() -> dict:
    rows = db.session.execute(
        db.text(
            """
            SELECT status, COUNT(*) AS n
            FROM geocode_post_commit_job
            GROUP BY status
            """
        )
    ).fetchall()
    return {str(r[0]): int(r[1]) for r in rows}


def _geo_counts_recent(hours: int = 24) -> dict:
    rows = db.session.execute(
        db.text(
            """
            SELECT g.geo_status, COUNT(*) AS n
            FROM domicilio_geocode g
            JOIN domicilio d ON d.id = g.domicilio_id
            JOIN relevamiento r ON r.domicilio_id = d.id
            WHERE r.created_at >= DATE_SUB(NOW(), INTERVAL :hours HOUR)
            GROUP BY g.geo_status
            """
        ),
        {"hours": hours},
    ).fetchall()
    return {str(r[0]): int(r[1]) for r in rows}


def _recent_relevamientos(limit: int = 10) -> list[dict]:
    rows = (
        db.session.query(Relevamiento, Domicilio)
        .join(Domicilio, Relevamiento.domicilio_id == Domicilio.id)
        .order_by(Relevamiento.id.desc())
        .limit(limit)
        .all()
    )
    out = []
    for rel, dom in rows:
        out.append(
            {
                "relevamiento_id": rel.id,
                "domicilio_id": dom.id,
                "calle": dom.calle,
                "numero": dom.numero,
                "created_at": rel.created_at.isoformat() if rel.created_at else None,
                "geo": _geo_snapshot(int(dom.id)),
                "jobs": _job_snapshot(int(dom.id)),
            }
        )
    return out


def _create_batch(n: int) -> list[dict]:
    rev = get_or_create_test_relevador()
    rub = get_test_rubro()
    created = []
    for i in range(n):
        calle = uniq(f"DiagGeo12_{i}")
        rel = crear_relevamiento_desde_payload(
            {
                "fecha": date.today().isoformat(),
                "relevadores_nombres": [rev.nombre],
                "domicilio": {"calle": calle, "numero": str(1000 + i)},
                "rubro_nombre": rub.nombre,
            }
        )
        dom_id = int(rel.domicilio_id)
        enqueued = schedule_geocode_after_grid_commit([dom_id])
        created.append(
            {
                "relevamiento_id": rel.id,
                "domicilio_id": dom_id,
                "calle": calle,
                "enqueued": enqueued,
                "before": _geo_snapshot(dom_id),
                "jobs_after_enqueue": _job_snapshot(dom_id),
            }
        )
    return created


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-cli", action="store_true", help="Ejecutar flask CLI drain")
    parser.add_argument("--create-batch", type=int, default=0, help="Crear N relevamientos de prueba")
    parser.add_argument("--trace-dom", type=int, default=0, help="Trazar pipeline para domicilio_id")
    parser.add_argument("--sync-pipeline", type=int, default=0, help="Ejecutar pipeline_post_commit sync")
    args = parser.parse_args()

    app = create_app()
    report: dict = {}

    with app.app_context():
        report["env"] = _env_report()
        init_geocode_post_commit_worker(app)
        report["worker_after_create_app"] = _worker_report(app)
        report["queue_counts"] = _queue_counts()
        report["geo_counts_relevamientos_24h"] = _geo_counts_recent(24)
        report["recent_relevamientos"] = _recent_relevamientos(10)

        if args.create_batch > 0:
            report["created_batch"] = _create_batch(args.create_batch)
            report["queue_counts_after_enqueue"] = _queue_counts()
            report["drain_scheduled"] = schedule_geocode_post_commit_drain()
            time.sleep(3.0)
            report["queue_counts_after_wait_3s"] = _queue_counts()
            for item in report["created_batch"]:
                dom_id = item["domicilio_id"]
                item["after_wait"] = _geo_snapshot(dom_id)
                item["jobs_after_wait"] = _job_snapshot(dom_id)

        if args.run_cli:
            report["cli_before"] = _queue_counts()
            summary = process_geocode_post_commit_jobs(limit=50)
            report["cli_summary"] = summary
            report["cli_after"] = _queue_counts()
            if report["recent_relevamientos"]:
                dom_id = report["recent_relevamientos"][0]["domicilio_id"]
                report["cli_sample_after"] = {
                    "domicilio_id": dom_id,
                    "geo": _geo_snapshot(dom_id),
                    "jobs": _job_snapshot(dom_id),
                }

        if args.trace_dom:
            report["pipeline_trace"] = _trace_pipeline(args.trace_dom)

        if args.sync_pipeline:
            before = _geo_snapshot(args.sync_pipeline)
            result = pipeline_post_commit(args.sync_pipeline)
            after = _geo_snapshot(args.sync_pipeline)
            report["sync_pipeline"] = {"before": before, "result": result, "after": after}

        if not args.create_batch and not args.run_cli and report["recent_relevamientos"]:
            sample = report["recent_relevamientos"][0]
            dom_id = sample["domicilio_id"]
            report["sample_trace"] = _trace_pipeline(dom_id)
            report["sync_vs_async"] = {
                "async_geo_before": sample["geo"],
            }
            # sync on same dom (read-only diagnostic: may mutate)
            before = _geo_snapshot(dom_id)
            sync_result = pipeline_post_commit(dom_id)
            after = _geo_snapshot(dom_id)
            report["sync_vs_async"]["sync_result"] = sync_result
            report["sync_vs_async"]["before"] = before
            report["sync_vs_async"]["after"] = after
            db.session.rollback()

    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
