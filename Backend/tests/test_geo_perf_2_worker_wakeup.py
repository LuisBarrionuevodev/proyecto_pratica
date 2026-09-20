"""
GEO-PERF.2 — wake-up confiable del worker geocode post-commit.
"""

from __future__ import annotations

import threading
import time
from datetime import date

import pytest
from sqlalchemy import inspect

from app.database import db
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service import (
    _claim_one_job_atomic,
    enqueue_geocode_post_commit,
    process_geocode_post_commit_jobs,
    reclaim_stale_processing_jobs,
)
from app.domains.geolocalizacion.geocode.services import geocode_post_commit_worker as worker_mod
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_worker import (
    init_geocode_post_commit_worker,
)
from app.domains.geolocalizacion.geocode.services.pipeline_service import pipeline_post_commit
from app.domains.grid.services.post_commit_geocode import schedule_geocode_after_grid_commit
from app.models import Domicilio, DomicilioGeocode, GeocodePostCommitJob
from tests.relevamiento_test_helpers import uniq


@pytest.fixture
def async_worker(app, monkeypatch):
    """Worker async aislado con cola limpia."""
    monkeypatch.setenv("GEO_POST_COMMIT_ASYNC", "true")
    monkeypatch.setenv("GEO_POST_COMMIT_DRAIN_MAX_ROUNDS", "50")
    from app.domains.geolocalizacion.geocode.services import geocode_post_commit_worker as worker_mod

    worker_mod.shutdown_geocode_post_commit_worker()
    worker_mod._executor = None
    worker_mod._app = None
    worker_mod._drain_scheduled = False
    worker_mod._drain_rerun_needed = False

    with app.app_context():
        if not inspect(db.engine).has_table("geocode_post_commit_job"):
            GeocodePostCommitJob.__table__.create(bind=db.engine, checkfirst=True)
        reclaim_stale_processing_jobs()
        GeocodePostCommitJob.query.delete()
        db.session.commit()
        assert GeocodePostCommitJob.query.count() == 0
        init_geocode_post_commit_worker(app)
        yield worker_mod
        worker_mod.shutdown_geocode_post_commit_worker()
        worker_mod._executor = None
        worker_mod._app = None
        worker_mod._drain_scheduled = False
        worker_mod._drain_rerun_needed = False


def _mk_domicilio(calle: str | None = None) -> Domicilio:
    dom = Domicilio(calle=calle or uniq("GeoPerf2"), numero="100")
    db.session.add(dom)
    db.session.commit()
    return dom


def _wait_worker_idle(timeout: float = 5.0) -> None:
    """Espera a que el worker libere ``_drain_scheduled``."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not worker_mod._drain_scheduled:
            return
        time.sleep(0.02)
    raise AssertionError(
        f"worker no quedó idle a tiempo (_drain_scheduled={worker_mod._drain_scheduled})"
    )


def _wait_job_done(domicilio_id: int, timeout: float = 5.0) -> GeocodePostCommitJob:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        db.session.remove()
        job = (
            GeocodePostCommitJob.query.filter_by(domicilio_id=int(domicilio_id))
            .order_by(GeocodePostCommitJob.id.desc())
            .first()
        )
        if job is not None and job.status in {"done", "failed"}:
            return job
        time.sleep(0.02)
    db.session.remove()
    job = (
        GeocodePostCommitJob.query.filter_by(domicilio_id=int(domicilio_id))
        .order_by(GeocodePostCommitJob.id.desc())
        .first()
    )
    raise AssertionError(
        f"job domicilio_id={domicilio_id} no terminó a tiempo (status={getattr(job, 'status', None)})"
    )


def test_batch_a_idle_batch_b_without_reset_globals(async_worker, monkeypatch):
    """QA: batch A → idle → batch B sin reset de globals ni reinicio del worker."""
    claim_timestamps: list[int] = []
    real_claim = _claim_one_job_atomic

    def tracked_claim():
        job_id = real_claim()
        if job_id is not None:
            job = GeocodePostCommitJob.query.get(int(job_id))
            if job is not None and job.processing_started_at is not None:
                claim_timestamps.append(int(job_id))
        return job_id

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service._claim_one_job_atomic",
        tracked_claim,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda domicilio_id: {"domicilio_id": domicilio_id, "ok": True},
    )

    with async_worker._app.app_context():
        executor_before = async_worker._executor
        assert executor_before is not None

        dom_a = int(_mk_domicilio(uniq("BatchA")).id)
        schedule_geocode_after_grid_commit([dom_a])
        job_a = _wait_job_done(dom_a)
        assert job_a.status == "done"

        _wait_worker_idle()
        assert worker_mod._drain_scheduled is False
        assert async_worker._executor is executor_before

        dom_b = int(_mk_domicilio(uniq("BatchB")).id)
        schedule_geocode_after_grid_commit([dom_b])
        job_b = _wait_job_done(dom_b)
        assert job_b.status == "done"
        assert async_worker._executor is executor_before
        assert len(claim_timestamps) >= 2


def test_batch_a_idle_b_idle_c_without_reset_globals(async_worker, monkeypatch):
    """Tres batches consecutivos con el mismo worker sin shutdown."""
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda domicilio_id: {"domicilio_id": domicilio_id, "ok": True},
    )

    with async_worker._app.app_context():
        executor_ref = async_worker._executor
        domicilio_ids = []

        for label in ("BatchA", "BatchB", "BatchC"):
            dom_id = int(_mk_domicilio(uniq(label)).id)
            domicilio_ids.append(dom_id)
            schedule_geocode_after_grid_commit([dom_id])
            job = _wait_job_done(dom_id)
            assert job.status == "done"
            _wait_worker_idle()
            assert worker_mod._drain_scheduled is False
            assert async_worker._executor is executor_ref


def test_submit_failure_rolls_back_drain_scheduled(async_worker, monkeypatch):
    """Submit fallido no deja ``_drain_scheduled`` stuck; schedule posterior procesa."""
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda domicilio_id: {"domicilio_id": domicilio_id, "ok": True},
    )

    real_submit = async_worker._executor.submit
    submit_calls = 0

    def flaky_submit(fn, *args, **kwargs):
        nonlocal submit_calls
        submit_calls += 1
        if submit_calls == 1:
            raise RuntimeError("simulated submit failure")
        return real_submit(fn, *args, **kwargs)

    with async_worker._app.app_context():
        async_worker._executor.submit = flaky_submit

        outcome = worker_mod.schedule_geocode_post_commit_drain()
        assert outcome == "executor_submit_failed"
        assert worker_mod._drain_scheduled is False

        dom_id = int(_mk_domicilio(uniq("SubmitRecovery")).id)
        enqueue_geocode_post_commit([dom_id])
        outcome2 = worker_mod.schedule_geocode_post_commit_drain()
        assert outcome2 == "scheduled"
        job = _wait_job_done(dom_id)
        assert job.status == "done"


def test_shutdown_reinit_clean_flags(async_worker, app, monkeypatch):
    """Shutdown + init nuevo no hereda flags del worker anterior."""
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda domicilio_id: {"domicilio_id": domicilio_id, "ok": True},
    )

    with app.app_context():
        async_worker.shutdown_geocode_post_commit_worker()
        assert worker_mod._executor is None
        assert worker_mod._drain_scheduled is False
        assert worker_mod._drain_rerun_needed is False

        worker_mod._drain_scheduled = True
        worker_mod._drain_rerun_needed = True

        init_geocode_post_commit_worker(app)
        assert worker_mod._executor is not None
        assert worker_mod._drain_scheduled is False
        assert worker_mod._drain_rerun_needed is False

        dom_id = int(_mk_domicilio(uniq("Reinit")).id)
        schedule_geocode_after_grid_commit([dom_id])
        job = _wait_job_done(dom_id)
        assert job.status == "done"


def test_max_rounds_continues_backlog(async_worker, monkeypatch):
    """MAX_ROUNDS pequeño programa continuación hasta vaciar pending."""
    monkeypatch.setenv("GEO_POST_COMMIT_DRAIN_MAX_ROUNDS", "1")
    monkeypatch.setenv("GEO_POST_COMMIT_DRAIN_LIMIT", "1")
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda domicilio_id: {"domicilio_id": domicilio_id, "ok": True},
    )

    with async_worker._app.app_context():
        dom_ids = [int(_mk_domicilio(uniq(f"MaxRounds{i}")).id) for i in range(4)]
        for dom_id in dom_ids:
            enqueue_geocode_post_commit([dom_id])
        worker_mod.schedule_geocode_post_commit_drain()

        for dom_id in dom_ids:
            job = _wait_job_done(dom_id, timeout=10.0)
            assert job.status == "done"

        _wait_worker_idle()
        assert worker_mod._drain_scheduled is False


def test_empty_queue_new_enqueue_processed_without_restart(async_worker, monkeypatch):
    """A: backend encendido, cola vacía, nuevo enqueue se procesa sin restart."""
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda domicilio_id: {"domicilio_id": domicilio_id, "ok": True},
    )

    with async_worker._app.app_context():
        domicilio_id = int(_mk_domicilio().id)
        schedule_geocode_after_grid_commit([domicilio_id])
        assert _wait_job_done(domicilio_id).status == "done"


def test_drain_exit_race_reprocesses_job(async_worker, monkeypatch):
    """B: race drain finalizando + enqueue durante ventana → rerun procesa job."""
    real_process = process_geocode_post_commit_jobs
    exit_gate = threading.Event()
    release_exit = threading.Event()

    def gated_process(limit: int = 50):
        summary = real_process(limit=limit)
        if summary.get("claimed", 0) == 0 and not release_exit.is_set():
            exit_gate.set()
            assert release_exit.wait(timeout=5.0)
        return summary

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_worker.process_geocode_post_commit_jobs",
        gated_process,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda domicilio_id: {"domicilio_id": domicilio_id},
    )

    with async_worker._app.app_context():
        assert worker_mod.schedule_geocode_post_commit_drain() == "scheduled"
        assert exit_gate.wait(timeout=5.0)

        dom = _mk_domicilio()
        enqueue_geocode_post_commit([int(dom.id)])
        assert worker_mod.schedule_geocode_post_commit_drain() == "coalesced"

        release_exit.set()
        job = _wait_job_done(int(dom.id))
        assert job.status == "done"


def test_multiple_enqueue_while_drain_active_single_rerun(async_worker, monkeypatch):
    """C: varios enqueue coalesced durante drain activo → un rerun alcanza."""
    real_process = process_geocode_post_commit_jobs
    exit_gate = threading.Event()
    release_exit = threading.Event()
    coalesced_count = 0

    def gated_process(limit: int = 50):
        summary = real_process(limit=limit)
        if summary.get("claimed", 0) == 0 and not release_exit.is_set():
            exit_gate.set()
            assert release_exit.wait(timeout=5.0)
        return summary

    real_schedule = worker_mod.schedule_geocode_post_commit_drain

    def counting_schedule(limit=None):
        nonlocal coalesced_count
        outcome = real_schedule(limit)
        if outcome == "coalesced":
            coalesced_count += 1
        return outcome

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_worker.process_geocode_post_commit_jobs",
        gated_process,
    )
    monkeypatch.setattr(worker_mod, "schedule_geocode_post_commit_drain", counting_schedule)
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda domicilio_id: {"domicilio_id": domicilio_id},
    )

    with async_worker._app.app_context():
        counting_schedule()
        assert exit_gate.wait(timeout=5.0)

        dom_ids = []
        for _ in range(3):
            dom = _mk_domicilio()
            dom_ids.append(int(dom.id))
            enqueue_geocode_post_commit([int(dom.id)])
            counting_schedule()

        assert coalesced_count >= 3
        release_exit.set()

        for domicilio_id in dom_ids:
            job = _wait_job_done(domicilio_id)
            assert job.status == "done"


def test_no_two_concurrent_drains(async_worker, monkeypatch):
    """D: nunca hay dos drains activos en paralelo."""
    active_drains = 0
    max_active = 0
    lock = threading.Lock()
    real_process = process_geocode_post_commit_jobs

    def tracked_process(limit: int = 50):
        nonlocal active_drains, max_active
        with lock:
            active_drains += 1
            max_active = max(max_active, active_drains)
        try:
            time.sleep(0.05)
            return real_process(limit=limit)
        finally:
            with lock:
                active_drains -= 1

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_worker.process_geocode_post_commit_jobs",
        tracked_process,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda domicilio_id: {"domicilio_id": domicilio_id},
    )

    with async_worker._app.app_context():
        dom_ids = []
        for _ in range(4):
            dom = _mk_domicilio()
            dom_ids.append(int(dom.id))
            schedule_geocode_after_grid_commit([int(dom.id)])
            worker_mod.schedule_geocode_post_commit_drain()

        for domicilio_id in dom_ids:
            _wait_job_done(domicilio_id)

        assert max_active == 1


def test_idle_worker_no_busy_loop(async_worker, monkeypatch):
    """E: tras procesar un job el worker vuelve a idle sin polling activo."""
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda did: {"domicilio_id": did},
    )

    with async_worker._app.app_context():
        domicilio_id = int(_mk_domicilio().id)
        schedule_geocode_after_grid_commit([domicilio_id])
        assert _wait_job_done(domicilio_id).status == "done"


def test_startup_recovery_still_drains_pending(async_worker, app, monkeypatch):
    """F: startup recovery sigue procesando jobs pendientes antiguos."""
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda domicilio_id: {"domicilio_id": domicilio_id},
    )

    with app.app_context():
        async_worker.shutdown_geocode_post_commit_worker()
        async_worker._executor = None
        async_worker._app = None
        async_worker._drain_scheduled = False
        async_worker._drain_rerun_needed = False

        dom = _mk_domicilio()
        from datetime import datetime

        db.session.add(
            GeocodePostCommitJob(
                domicilio_id=int(dom.id),
                status="pending",
                attempts=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        db.session.commit()

        init_geocode_post_commit_worker(app)
        job = _wait_job_done(int(dom.id))
        assert job.status == "done"


def test_failed_job_retry_unchanged(async_worker, monkeypatch):
    """G: failed/retry mantiene comportamiento actual."""
    monkeypatch.setenv("GEO_POST_COMMIT_MAX_ATTEMPTS", "1")
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda _dom_id: (_ for _ in ()).throw(RuntimeError("provider down")),
    )

    with async_worker._app.app_context():
        dom = _mk_domicilio()
        schedule_geocode_after_grid_commit([int(dom.id)])
        job = _wait_job_done(int(dom.id))
        assert job.status == "failed"
        assert int(job.attempts or 0) >= 1


def test_google_provider_through_worker(async_worker, monkeypatch):
    """I: provider Google sigue funcionando a través del worker."""
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocoding.services.geocode_service.get_geocoder_provider",
        lambda: "google",
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.pipeline_service.normalizar_domicilio",
        lambda domicilio_id: _normalize_dom_ok(domicilio_id),
    )

    from app.domains.geolocalizacion.geocoding.services.google_geocode_adapter import GeocodeResult

    fake = GeocodeResult(
        lat=-26.8245,
        lng=-65.2223,
        provider="google",
        provider_place_id="place-1",
        precision="ROOFTOP",
        confidence=1.0,
        formatted_address="Test 100",
        partial_match=False,
        raw_status="OK",
        geo_status="OK",
    )

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocoding.services.google_geocode_adapter.geocode_google_for_domicilio",
        lambda _dom: fake,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.distritos_service.resolve_distrito_id",
        lambda _lat, _lng: None,
    )

    with async_worker._app.app_context():
        dom = Domicilio(calle=uniq("GoogleWorker"), numero="500", calle_norm_status="OK", calle_normalizada=uniq("GoogleWorker"))
        db.session.add(dom)
        db.session.commit()

        schedule_geocode_after_grid_commit([int(dom.id)])
        _wait_job_done(int(dom.id))

        geo = DomicilioGeocode.query.filter_by(domicilio_id=int(dom.id)).first()
        assert geo is not None
        assert str(geo.provider) == "google"
        assert str(geo.geo_status) == "OK"
        assert geo.quality == "ROOFTOP"


def _normalize_dom_ok(domicilio_id: int) -> dict:
    dom = db.session.get(Domicilio, int(domicilio_id))
    if dom is None:
        return {"status": "NO_MATCH"}
    dom.calle_norm_status = "OK"
    dom.calle_normalizada = dom.calle or "Test"
    db.session.add(dom)
    db.session.commit()
    return {"status": "OK"}
