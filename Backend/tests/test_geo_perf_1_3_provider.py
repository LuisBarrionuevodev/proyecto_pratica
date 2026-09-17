"""
GEO-PERF.1.3 — provider runtime, worker dev, semántica de jobs.
"""

from __future__ import annotations

import os
from datetime import datetime

import pytest
from sqlalchemy import inspect

from app.database import db
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service import (
    _process_claimed_job,
    process_geocode_post_commit_jobs,
)
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_worker import (
    _is_werkzeug_reloader_parent,
    init_geocode_post_commit_worker,
)
from app.domains.geolocalizacion.geocode.services.pipeline_service import pipeline_post_commit
from app.domains.geolocalizacion.geocoding.services.geocode_service import (
    _is_accepted,
    geocode_domicilio,
    get_geocoder_provider,
)
from app.models import Domicilio, DomicilioGeocode, GeocodePostCommitJob


@pytest.fixture
def app_ctx(app, monkeypatch):
    monkeypatch.setenv("GEO_POST_COMMIT_ASYNC", "false")
    with app.app_context():
        if not inspect(db.engine).has_table("geocode_post_commit_job"):
            GeocodePostCommitJob.__table__.create(bind=db.engine, checkfirst=True)
        GeocodePostCommitJob.query.delete()
        db.session.commit()
        yield app
        db.session.rollback()


def test_get_geocoder_provider_runtime_from_config(app_ctx, monkeypatch):
    """A: provider leído desde Flask config en runtime."""
    monkeypatch.delenv("GEOCODER_PROVIDER", raising=False)
    monkeypatch.delenv("GEO_PROVIDER", raising=False)
    app_ctx.config["GEOCODER_PROVIDER"] = "geoapify"
    assert get_geocoder_provider() == "geoapify"

    app_ctx.config["GEOCODER_PROVIDER"] = "nominatim"
    assert get_geocoder_provider() == "nominatim"


def test_import_previo_no_congela_provider(monkeypatch):
    """B: sin app config, el provider se resuelve desde env en runtime (no import-time)."""
    monkeypatch.delenv("GEOCODER_PROVIDER", raising=False)
    monkeypatch.delenv("GEO_PROVIDER", raising=False)
    assert get_geocoder_provider() == "geoapify"

    monkeypatch.setenv("GEOCODER_PROVIDER", "nominatim")
    assert get_geocoder_provider() == "nominatim"


def test_cambio_provider_runtime_sin_reload(app_ctx, monkeypatch):
    """C: cambio de provider sin reload del módulo."""
    app_ctx.config["GEOCODER_PROVIDER"] = "nominatim"
    assert get_geocoder_provider() == "nominatim"

    app_ctx.config["GEOCODER_PROVIDER"] = "geoapify"
    assert get_geocoder_provider() == "geoapify"


def test_geocode_usa_provider_runtime_geoapify(app_ctx, monkeypatch):
    """B/C: geocode_domicilio usa Geoapify aunque el módulo se importó sin env."""
    app_ctx.config["GEOCODER_PROVIDER"] = "geoapify"
    captured: list[str] = []

    def _fake_geoapify(query: str):
        captured.append(query)
        return {
            "features": [
                {
                    "geometry": {"coordinates": [-65.2026602, -26.8229733]},
                    "properties": {
                        "rank": {"confidence": 1.0},
                        "housenumber": "500",
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
        lambda _lat, _lng: None,
    )

    dom = Domicilio(
        calle="Corrientes",
        numero="500",
        calle_norm_status="OK",
        calle_normalizada="Corrientes",
    )
    db.session.add(dom)
    db.session.flush()
    db.session.add(DomicilioGeocode(domicilio_id=dom.id, geo_status="GEO_PENDING", source="AUTO"))
    db.session.commit()

    result = geocode_domicilio(int(dom.id))
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()

    assert captured
    assert result["provider"] == "geoapify"
    assert geo is not None
    assert geo.provider == "geoapify"
    assert geo.geo_status == "OK"
    assert _is_accepted(geo.quality, float(geo.score))


def test_corrientes_500_geoapify_building_score(app_ctx, monkeypatch):
    """F: Corrientes 500 con Geoapify pasa regla AUTO actual."""
    app_ctx.config["GEOCODER_PROVIDER"] = "geoapify"
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocoding.services.geocode_service._request_geoapify",
        lambda _q: {
            "features": [
                {
                    "geometry": {"coordinates": [-65.2026602, -26.8229733]},
                    "properties": {
                        "rank": {"confidence": 1.0},
                        "housenumber": "500",
                        "result_type": "building",
                    },
                }
            ]
        },
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.distritos_service.resolve_distrito_id",
        lambda _lat, _lng: None,
    )

    dom = Domicilio(
        calle="Corrientes",
        numero="500",
        calle_norm_status="OK",
        calle_normalizada="Corrientes",
    )
    db.session.add(dom)
    db.session.flush()
    db.session.add(DomicilioGeocode(domicilio_id=dom.id, geo_status="GEO_PENDING", source="AUTO"))
    db.session.commit()

    geocode_domicilio(int(dom.id))
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert geo is not None
    assert geo.quality == "building"
    assert float(geo.score) >= 0.95
    assert geo.geo_status == "OK"


def test_werkzeug_child_inicia_worker(app, monkeypatch):
    """F: hijo del reloader inicia worker."""
    from app.domains.geolocalizacion.geocode.services import geocode_post_commit_worker as worker_mod

    worker_mod.shutdown_geocode_post_commit_worker()
    worker_mod._executor = None
    worker_mod._app = None

    monkeypatch.setenv("GEO_POST_COMMIT_ASYNC", "true")
    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "true")
    init_geocode_post_commit_worker(app)
    assert worker_mod._executor is not None


def test_job_done_con_geo_ok(app_ctx, monkeypatch):
    """G: job done + geo OK."""
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda dom_id: None,
    )
    dom = Domicilio(calle="Corrientes", numero="500", calle_norm_status="OK", calle_normalizada="Corrientes")
    db.session.add(dom)
    db.session.flush()
    db.session.add(
        DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status="OK",
            lat=-26.82,
            lng=-65.20,
            provider="geoapify",
            source="AUTO",
        )
    )
    db.session.commit()

    now = datetime.utcnow()
    job = GeocodePostCommitJob(
        domicilio_id=dom.id,
        status="processing",
        attempts=0,
        processing_started_at=now,
        created_at=now,
        updated_at=now,
    )
    db.session.add(job)
    db.session.commit()

    summary = {"processed": 0, "done": 0, "failed": 0, "skipped": 0, "requeued": 0}
    _process_claimed_job(int(job.id), summary)

    refreshed = db.session.get(GeocodePostCommitJob, job.id)
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert refreshed is not None
    assert refreshed.status == "done"
    assert geo is not None
    assert geo.geo_status == "OK"


def test_job_done_con_geo_pending_no_requeue_infinito(app_ctx, monkeypatch):
    """H/I: done + GEO_PENDING no reencola por estado funcional."""
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda dom_id: None,
    )
    dom = Domicilio(calle="Corrientes", numero="500", calle_norm_status="OK", calle_normalizada="Corrientes")
    db.session.add(dom)
    db.session.flush()
    db.session.add(
        DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status="GEO_PENDING",
            lat=-26.82,
            lng=-65.20,
            provider="geoapify",
            quality="street",
            score=0.5,
            source="AUTO",
        )
    )
    db.session.commit()

    now = datetime.utcnow()
    job = GeocodePostCommitJob(
        domicilio_id=dom.id,
        status="pending",
        attempts=0,
        created_at=now,
        updated_at=now,
    )
    db.session.add(job)
    db.session.commit()
    dom_id = int(dom.id)
    job_id = int(job.id)

    summary = process_geocode_post_commit_jobs(limit=1)
    refreshed = db.session.get(GeocodePostCommitJob, job_id)
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom_id).first()

    assert summary["done"] == 1
    assert summary.get("requeued", 0) == 0
    assert refreshed is not None
    assert refreshed.status == "done"
    assert geo is not None
    assert geo.geo_status == "GEO_PENDING"


def test_job_done_con_norm_pending_no_requeue(app_ctx, monkeypatch):
    """I: NORM_PENDING no genera retry infinito."""
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda dom_id: None,
    )
    dom = Domicilio(calle="Calle Inventada", numero="99", calle_norm_status="REVIEW")
    db.session.add(dom)
    db.session.flush()
    db.session.add(
        DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status="NORM_PENDING",
            source="AUTO",
        )
    )
    db.session.commit()

    now = datetime.utcnow()
    job = GeocodePostCommitJob(
        domicilio_id=dom.id,
        status="pending",
        attempts=0,
        created_at=now,
        updated_at=now,
    )
    db.session.add(job)
    db.session.commit()

    summary = process_geocode_post_commit_jobs(limit=1)
    refreshed = db.session.get(GeocodePostCommitJob, job.id)

    assert summary["done"] == 1
    assert summary.get("requeued", 0) == 0
    assert refreshed is not None
    assert refreshed.status == "done"


def test_sync_vs_async_mismo_geo_status(app_ctx, monkeypatch):
    """J: pipeline sync y job async comparten resultado geo."""
    app_ctx.config["GEOCODER_PROVIDER"] = "geoapify"

    def _fake_pipeline(dom_id: int):
        geo = DomicilioGeocode.query.filter_by(domicilio_id=int(dom_id)).first()
        if geo:
            geo.geo_status = "GEO_PENDING"
            geo.provider = "geoapify"
            geo.quality = "street"
            geo.score = 0.5
            db.session.add(geo)
            db.session.commit()
        return {"domicilio_id": dom_id}

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        _fake_pipeline,
    )

    dom = Domicilio(calle="Corrientes", numero="600", calle_norm_status="OK", calle_normalizada="Corrientes")
    db.session.add(dom)
    db.session.flush()
    db.session.add(DomicilioGeocode(domicilio_id=dom.id, geo_status="GEO_PENDING", source="AUTO"))
    db.session.commit()

    dom_id = int(dom.id)
    sync_result = _fake_pipeline(dom_id)
    sync_geo = DomicilioGeocode.query.filter_by(domicilio_id=dom_id).first()
    sync_status = str(sync_geo.geo_status) if sync_geo else None
    sync_provider = str(sync_geo.provider) if sync_geo and sync_geo.provider else None

    now = datetime.utcnow()
    job = GeocodePostCommitJob(
        domicilio_id=dom.id,
        status="pending",
        attempts=0,
        created_at=now,
        updated_at=now,
    )
    db.session.add(job)
    db.session.commit()
    process_geocode_post_commit_jobs(limit=1)
    async_geo = DomicilioGeocode.query.filter_by(domicilio_id=dom_id).first()
    async_status = str(async_geo.geo_status) if async_geo else None
    async_provider = str(async_geo.provider) if async_geo and async_geo.provider else None

    assert sync_result["domicilio_id"] == dom_id
    assert sync_status == async_status == "GEO_PENDING"
    assert sync_provider == async_provider == "geoapify"


def test_werkzeug_reloader_parent_flag():
    """E: supervisor explícito detectado."""
    old = os.environ.get("WERKZEUG_RUN_MAIN")
    os.environ["WERKZEUG_RUN_MAIN"] = "false"
    assert _is_werkzeug_reloader_parent() is True
    os.environ["WERKZEUG_RUN_MAIN"] = "true"
    assert _is_werkzeug_reloader_parent() is False
    if old is None:
        os.environ.pop("WERKZEUG_RUN_MAIN", None)
    else:
        os.environ["WERKZEUG_RUN_MAIN"] = old
