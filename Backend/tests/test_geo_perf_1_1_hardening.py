"""
GEO-PERF.1.1 — hardening cola geocode post-commit.
"""

from __future__ import annotations

import threading
import time
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import inspect, text

from app.database import db
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service import (
    _claim_one_job_atomic,
    enqueue_geocode_post_commit,
    process_geocode_post_commit_jobs,
    reclaim_stale_processing_jobs,
)
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_worker import (
    _is_werkzeug_reloader_parent,
    init_geocode_post_commit_worker,
)
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import compute_addr_hash
from app.domains.grid.services.post_commit_geocode import schedule_geocode_after_grid_commit
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.models import Domicilio, DomicilioGeocode, GeocodePostCommitJob
from tests.relevamiento_test_helpers import get_or_create_test_relevador, get_test_rubro, uniq


@pytest.fixture
def app_ctx(app, actor_user_id, monkeypatch):
    from tests.helpers.service_actor import geocode_job_app_ctx

    monkeypatch.setenv("GEO_POST_COMMIT_ASYNC", "false")
    monkeypatch.setenv("GEO_POST_COMMIT_PROCESSING_LEASE_SEC", "1")
    with geocode_job_app_ctx(app, actor_user_id) as ctx_app:
        yield ctx_app


def _mk_payload(calle: str | None = None, numero: str = "1500") -> dict:
    rev = get_or_create_test_relevador()
    rub = get_test_rubro()
    return {
        "fecha": date.today().isoformat(),
        "relevadores_nombres": [rev.nombre],
        "domicilio": {"calle": calle or uniq("GeoPerf11"), "numero": numero},
        "rubro_nombre": rub.nombre,
    }


def _add_pending_job(domicilio_id: int) -> GeocodePostCommitJob:
    now = datetime.utcnow()
    job = GeocodePostCommitJob(
        domicilio_id=int(domicilio_id),
        status="pending",
        attempts=0,
        created_at=now,
        updated_at=now,
    )
    db.session.add(job)
    db.session.commit()
    return job


def test_dos_workers_solo_uno_claim(app_ctx, monkeypatch):
    """A: dos workers no reclaman el mismo job."""
    dom = Domicilio(calle=uniq("ClaimRace"), numero="10")
    db.session.add(dom)
    db.session.commit()
    job = _add_pending_job(dom.id)

    claimed_ids: list[int] = []
    lock = threading.Lock()

    def _worker():
        with app_ctx.app_context():
            claimed_id = _claim_one_job_atomic()
            if claimed_id is not None:
                with lock:
                    claimed_ids.append(int(claimed_id))
            db.session.remove()

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert claimed_ids == [job.id]
    refreshed = db.session.get(GeocodePostCommitJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "processing"


def test_pending_sobrevive_restart(app_ctx, monkeypatch):
    """B: pending previo al restart se procesa."""
    dom = Domicilio(calle=uniq("RestartPending"), numero="11")
    db.session.add(dom)
    db.session.commit()
    _add_pending_job(dom.id)

    calls: list[int] = []

    def _pipe(dom_id: int):
        calls.append(int(dom_id))
        return {"domicilio_id": dom_id}

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        _pipe,
    )
    dom_id = int(dom.id)
    summary = process_geocode_post_commit_jobs(limit=5)
    assert summary["claimed"] >= 1
    assert dom_id in calls


def test_processing_abandonado_se_recupera(app_ctx):
    """C: processing con lease expirado vuelve a pending y se procesa."""
    dom = Domicilio(calle=uniq("StaleProc"), numero="12")
    db.session.add(dom)
    db.session.commit()
    now = datetime.utcnow()
    job = GeocodePostCommitJob(
        domicilio_id=dom.id,
        status="processing",
        attempts=0,
        processing_started_at=now - timedelta(seconds=30),
        created_at=now,
        updated_at=now,
    )
    db.session.add(job)
    db.session.commit()

    reclaimed = reclaim_stale_processing_jobs()
    assert reclaimed == 1
    refreshed = db.session.get(GeocodePostCommitJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "pending"


def test_failed_no_se_recupera_automaticamente(app_ctx, monkeypatch):
    """D: failed definitivo no vuelve a pending."""
    dom = Domicilio(calle=uniq("FailedStay"), numero="13")
    db.session.add(dom)
    db.session.commit()
    now = datetime.utcnow()
    job = GeocodePostCommitJob(
        domicilio_id=dom.id,
        status="failed",
        attempts=3,
        last_error="permanent",
        processing_started_at=now - timedelta(seconds=3600),
        created_at=now,
        updated_at=now,
    )
    db.session.add(job)
    db.session.commit()

    reclaimed = reclaim_stale_processing_jobs()
    assert reclaimed == 0
    summary = process_geocode_post_commit_jobs(limit=5)
    assert summary["claimed"] == 0
    refreshed = db.session.get(GeocodePostCommitJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "failed"


def test_cli_y_worker_concurrentes_una_ejecucion(app_ctx, monkeypatch):
    """E: claim atómico evita doble ejecución lógica."""
    dom = Domicilio(calle=uniq("Concurrent"), numero="14")
    db.session.add(dom)
    db.session.commit()
    _add_pending_job(dom.id)

    processed: list[int] = []
    barrier = threading.Barrier(2)

    def _pipe(dom_id: int):
        processed.append(int(dom_id))
        time.sleep(0.05)
        return {"domicilio_id": dom_id}

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        _pipe,
    )

    results: list[dict] = []

    def _run():
        barrier.wait(timeout=3.0)
        with app_ctx.app_context():
            results.append(process_geocode_post_commit_jobs(limit=1))
            db.session.remove()

    t1 = threading.Thread(target=_run)
    t2 = threading.Thread(target=_run)
    t1.start()
    t2.start()
    t1.join(timeout=10.0)
    t2.join(timeout=10.0)

    total_claimed = sum(r.get("claimed", 0) for r in results)
    assert total_claimed == 1
    assert processed == [dom.id]


def test_direccion_cambia_mientras_job_espera(app_ctx, monkeypatch):
    """F: geocode final corresponde a dirección nueva, no a la encolada."""
    app_ctx.config["GEOCODER_PROVIDER"] = "geoapify"
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.pipeline_service.normalizar_domicilio",
        lambda dom_id: {"status": "OK"},
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocoding.services.geocode_service.get_geocoder_provider",
        lambda: "geoapify",
    )

    captured_queries: list[str] = []

    def _fake_geoapify(query: str):
        captured_queries.append(query)
        return {
            "features": [
                {
                    "geometry": {"coordinates": [-65.2223, -26.8245]},
                    "properties": {
                        "rank": {"confidence": 0.99},
                        "housenumber": "600",
                        "result_type": "building",
                    },
                }
            ]
        }

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocoding.services.geocode_service._request_geoapify",
        _fake_geoapify,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.distritos_service.resolve_distrito_id",
        lambda _lat, _lng: 1,
    )

    dom = Domicilio(calle="Corrientes", numero="500", calle_norm_status="OK", calle_normalizada="Corrientes")
    db.session.add(dom)
    db.session.flush()
    db.session.add(DomicilioGeocode(domicilio_id=dom.id, geo_status="GEO_PENDING", source="AUTO"))
    db.session.commit()

    job = _add_pending_job(dom.id)

    claimed_id = _claim_one_job_atomic()
    assert claimed_id is not None
    claimed = db.session.get(GeocodePostCommitJob, claimed_id)
    assert claimed is not None
    old_hash = str(claimed.claimed_addr_hash)
    assert old_hash == compute_addr_hash(dom)

    dom.numero = "600"
    dom.calle_normalizada = "Corrientes"
    db.session.add(dom)
    db.session.commit()

    summary: dict = {
        "processed": 0,
        "done": 0,
        "failed": 0,
        "skipped": 0,
        "requeued": 0,
    }
    from app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service import (
        _process_claimed_job,
    )

    _process_claimed_job(int(claimed_id), summary)

    refreshed_job = db.session.get(GeocodePostCommitJob, job.id)
    assert refreshed_job is not None
    assert refreshed_job.status in {"pending", "done"}
    assert any("600" in q for q in captured_queries)
    assert not any(" 500," in q or " 500 " in q for q in captured_queries)


def test_excepcion_provider_rollback_limpio(app_ctx, monkeypatch):
    """G: excepción deja sesión reutilizable y attempts correcto."""
    dom = Domicilio(calle=uniq("SqlRollback"), numero="15")
    db.session.add(dom)
    db.session.commit()
    job = _add_pending_job(dom.id)
    monkeypatch.setenv("GEO_POST_COMMIT_MAX_ATTEMPTS", "3")

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda _dom_id: (_ for _ in ()).throw(RuntimeError("provider down")),
    )

    summary = process_geocode_post_commit_jobs(limit=1)
    assert summary["claimed"] == 1
    refreshed = db.session.get(GeocodePostCommitJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "pending"
    assert refreshed.attempts == 1

    # Sesión reutilizable: otra operación simple no debe fallar.
    count = db.session.execute(text("SELECT COUNT(*) FROM geocode_post_commit_job")).scalar()
    assert int(count or 0) >= 1


def test_no_duplicar_job_si_processing(app_ctx):
    """H: domicilio con job processing no recibe segundo job."""
    dom = Domicilio(calle=uniq("NoDupProc"), numero="16")
    db.session.add(dom)
    db.session.commit()
    now = datetime.utcnow()
    db.session.add(
        GeocodePostCommitJob(
            domicilio_id=dom.id,
            status="processing",
            attempts=0,
            processing_started_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    db.session.commit()

    enqueued = enqueue_geocode_post_commit([dom.id])
    assert enqueued == []
    active = GeocodePostCommitJob.query.filter(
        GeocodePostCommitJob.domicilio_id == dom.id,
        GeocodePostCommitJob.status.in_(("pending", "processing")),
    ).count()
    assert active == 1


def test_retries_tres_intentos_a_failed(app_ctx, monkeypatch):
    """Retries: 1→pending, 2→pending, 3→failed."""
    dom = Domicilio(calle=uniq("Retries"), numero="17")
    db.session.add(dom)
    db.session.commit()
    job = _add_pending_job(dom.id)
    monkeypatch.setenv("GEO_POST_COMMIT_MAX_ATTEMPTS", "3")
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda _dom_id: (_ for _ in ()).throw(RuntimeError("fail")),
    )

    for expected_attempts, expected_status in [(1, "pending"), (2, "pending"), (3, "failed")]:
        process_geocode_post_commit_jobs(limit=1)
        refreshed = db.session.get(GeocodePostCommitJob, job.id)
        assert refreshed is not None
        assert refreshed.attempts == expected_attempts
        assert refreshed.status == expected_status


def test_werkzeug_reloader_parent_skip(monkeypatch):
    """Reloader: solo el supervisor explícito (WERKZEUG_RUN_MAIN=false) omite worker."""
    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "false")
    assert _is_werkzeug_reloader_parent() is True

    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "true")
    assert _is_werkzeug_reloader_parent() is False

    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    monkeypatch.setenv("FLASK_DEBUG", "1")
    assert _is_werkzeug_reloader_parent() is False


def test_init_worker_debug_sin_reloader(app, monkeypatch):
    """GEO-PERF.1.3: FLASK_DEBUG=1 sin reloader debe iniciar worker."""
    from app.domains.geolocalizacion.geocode.services import geocode_post_commit_worker as worker_mod

    worker_mod.shutdown_geocode_post_commit_worker()
    worker_mod._executor = None
    worker_mod._app = None

    monkeypatch.setenv("GEO_POST_COMMIT_ASYNC", "true")
    monkeypatch.setenv("FLASK_DEBUG", "1")
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    init_geocode_post_commit_worker(app)
    assert worker_mod._executor is not None


def test_init_worker_no_doble_en_reloader_parent(app, monkeypatch):
    from app.domains.geolocalizacion.geocode.services import geocode_post_commit_worker as worker_mod

    worker_mod.shutdown_geocode_post_commit_worker()
    worker_mod._executor = None
    worker_mod._app = None

    monkeypatch.setenv("GEO_POST_COMMIT_ASYNC", "true")
    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "false")
    init_geocode_post_commit_worker(app)
    assert worker_mod._executor is None
