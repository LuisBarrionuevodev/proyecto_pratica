"""
GEO-PERF.1 — geocode post-commit async desde grid commit.
"""

from __future__ import annotations

import threading
import time
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from app.database import db
from app.domains.domicilios.services.domicilio_completar_trabajo_service import (
    heredar_geocode_domicilio_desde_origen,
)
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service import (
    domicilio_necesita_geocode_post_commit,
    enqueue_geocode_post_commit,
    process_geocode_post_commit_jobs,
)
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_worker import (
    init_geocode_post_commit_worker,
    schedule_geocode_post_commit_drain,
)
from app.domains.geolocalizacion.geocode.services.pipeline_service import pipeline_post_commit
from app.domains.grid.services.post_commit_geocode import schedule_geocode_after_grid_commit
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.models import Domicilio, DomicilioGeocode, GeocodePostCommitJob, Relevamiento
from tests.relevamiento_test_helpers import get_or_create_test_relevador, get_test_rubro, uniq


@pytest.fixture
def app_ctx(app, monkeypatch):
    monkeypatch.setenv("GEO_POST_COMMIT_ASYNC", "false")
    with app.app_context():
        if not inspect(db.engine).has_table("geocode_post_commit_job"):
            GeocodePostCommitJob.__table__.create(bind=db.engine, checkfirst=True)
        # Aislar tests de jobs pendientes reales en la BD de desarrollo.
        GeocodePostCommitJob.query.delete()
        db.session.commit()
        yield app
        db.session.rollback()


def _mock_normalizar_domicilio_ok(domicilio_id: int) -> dict:
    dom = db.session.get(Domicilio, int(domicilio_id))
    if dom is None:
        return {"status": "NO_MATCH"}
    dom.calle_norm_status = "OK"
    dom.calle_normalizada = dom.calle or "Test"
    db.session.add(dom)
    db.session.commit()
    return {"status": "OK", "calle": dom.calle_normalizada}


def _mk_payload(calle: str | None = None, numero: str = "1500") -> dict:
    rev = get_or_create_test_relevador()
    rub = get_test_rubro()
    return {
        "fecha": date.today().isoformat(),
        "relevadores_nombres": [rev.nombre],
        "domicilio": {"calle": calle or uniq("GeoPerf1"), "numero": numero},
        "rubro_nombre": rub.nombre,
    }


def test_commit_batch_responde_sin_esperar_provider_lento(app, client, auth_headers, monkeypatch):
    """A: HTTP no espera pipeline lento cuando async está habilitado."""
    monkeypatch.setenv("GEO_POST_COMMIT_ASYNC", "true")
    started = threading.Event()
    release = threading.Event()

    real_pipeline = pipeline_post_commit

    def _slow_pipeline(domicilio_id: int):
        started.set()
        assert release.wait(timeout=5.0)
        return real_pipeline(domicilio_id)

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        _slow_pipeline,
    )

    with app.app_context():
        if not inspect(db.engine).has_table("geocode_post_commit_job"):
            GeocodePostCommitJob.__table__.create(bind=db.engine, checkfirst=True)
        init_geocode_post_commit_worker(app)

        start = client.post("/grid/start", headers=auth_headers, json={"kind": "relevamientos"})
        batch_id = start.get_json()["batch_id"]
        calle = uniq("GeoPerfSlow")
        payload = _mk_payload(calle=calle)

        t0 = time.perf_counter()
        resp = client.post(
            "/grid/commit-batch",
            headers=auth_headers,
            json={
                "batch_id": batch_id,
                "rows": [{"row_id": "r1", "normalized": payload}],
            },
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert resp.status_code == 200
        assert resp.get_json()["results"][0]["ok"] is True
        assert elapsed_ms < 2000.0
        assert started.wait(timeout=3.0)
        release.set()
        time.sleep(0.5)
        from app.domains.geolocalizacion.geocode.services import geocode_post_commit_worker as worker_mod

        worker_mod.shutdown_geocode_post_commit_worker()
        worker_mod._executor = None
        worker_mod._app = None
        worker_mod._drain_scheduled = False
        worker_mod._drain_rerun_needed = False


def test_relevamiento_persistido_antes_del_geocode(app_ctx, monkeypatch):
    """B: relevamiento existe antes de procesar cola."""
    calls: list[int] = []

    rel = crear_relevamiento_desde_payload(_mk_payload())
    assert rel.id is not None
    target_dom_id = int(rel.domicilio_id)

    def _track_pipeline(domicilio_id: int):
        if int(domicilio_id) != target_dom_id:
            return {"domicilio_id": domicilio_id}
        rel_count = Relevamiento.query.filter_by(domicilio_id=target_dom_id).count()
        calls.append(rel_count)
        geo = DomicilioGeocode.query.filter_by(domicilio_id=target_dom_id).first()
        if geo is not None:
            geo.geo_status = "OK"
            geo.lat = -26.8245
            geo.lng = -65.2223
            db.session.add(geo)
            db.session.commit()
        return {"domicilio_id": domicilio_id}

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        _track_pipeline,
    )

    schedule_geocode_after_grid_commit([target_dom_id])
    assert calls == [1]


def test_job_ejecuta_pipeline_y_geo_ok(app_ctx, monkeypatch):
    """C: worker ejecuta pipeline existente."""
    app_ctx.config["GEOCODER_PROVIDER"] = "geoapify"
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocoding.services.geocode_service.get_geocoder_provider",
        lambda: "geoapify",
    )
    dist = db.session.execute(db.text("SELECT id FROM distrito ORDER BY id ASC LIMIT 1")).scalar()
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.pipeline_service.normalizar_domicilio",
        _mock_normalizar_domicilio_ok,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.distritos_service.resolve_distrito_id",
        lambda _lat, _lng: dist,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocoding.services.geocode_service._request_geoapify",
        lambda _q: {
            "features": [
                {
                    "geometry": {"coordinates": [-65.2223, -26.8245]},
                    "properties": {
                        "rank": {"confidence": 0.99},
                        "housenumber": "1500",
                        "result_type": "building",
                    },
                }
            ]
        },
    )

    rel = crear_relevamiento_desde_payload(_mk_payload())
    domicilio_id = int(rel.domicilio_id)
    schedule_geocode_after_grid_commit([domicilio_id])

    geo = DomicilioGeocode.query.filter_by(domicilio_id=domicilio_id).first()
    assert geo is not None
    assert str(geo.geo_status) == "OK"
    dom = db.session.get(Domicilio, domicilio_id)
    assert dom is not None
    if dist is not None:
        assert dom.distrito_id == dist


def test_proveedor_falla_relevamiento_sigue(app_ctx, monkeypatch):
    """D: fallo de geocode no borra relevamiento."""
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        lambda _dom_id: (_ for _ in ()).throw(RuntimeError("provider down")),
    )
    monkeypatch.setenv("GEO_POST_COMMIT_MAX_ATTEMPTS", "1")

    rel = crear_relevamiento_desde_payload(_mk_payload())
    rel_id = int(rel.id)
    domicilio_id = int(rel.domicilio_id)
    schedule_geocode_after_grid_commit([domicilio_id])

    rel_ref = db.session.get(Relevamiento, rel_id)
    assert rel_ref is not None
    job = GeocodePostCommitJob.query.filter_by(domicilio_id=domicilio_id).first()
    assert job is not None
    assert job.status == "failed"


def test_enqueue_deduplica_mismo_domicilio(app_ctx):
    """E: un solo job pending por domicilio."""
    dom = Domicilio(calle=uniq("Dedup"), numero="10")
    db.session.add(dom)
    db.session.commit()

    first = enqueue_geocode_post_commit([dom.id, dom.id])
    second = enqueue_geocode_post_commit([dom.id])

    assert first == [dom.id]
    assert second == []
    pending = GeocodePostCommitJob.query.filter_by(domicilio_id=dom.id, status="pending").count()
    assert pending == 1


def test_geo_ok_no_genera_job(app_ctx):
    """F: domicilio con geo OK no encola trabajo."""
    dom = Domicilio(calle=uniq("GeoOk"), numero="20")
    db.session.add(dom)
    db.session.flush()
    db.session.add(
        DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status="OK",
            lat=-26.8245,
            lng=-65.2223,
            source="MANUAL",
        )
    )
    db.session.commit()

    assert domicilio_necesita_geocode_post_commit(int(dom.id)) is False
    assert enqueue_geocode_post_commit([dom.id]) == []


def test_cow_hereda_geocode_no_reencola(app_ctx):
    """G: COW con geocode heredado no necesita geocode post-commit."""
    origen = Domicilio(calle=uniq("CowOrigen"), numero="30")
    db.session.add(origen)
    db.session.flush()
    db.session.add(
        DomicilioGeocode(
            domicilio_id=origen.id,
            geo_status="OK",
            lat=-26.8245,
            lng=-65.2223,
            source="MANUAL",
            quality="MANUAL_EXACT",
        )
    )
    nuevo = Domicilio(calle=origen.calle, numero=origen.numero)
    db.session.add(nuevo)
    db.session.flush()
    heredar_geocode_domicilio_desde_origen(int(origen.id), int(nuevo.id))
    db.session.commit()

    assert domicilio_necesita_geocode_post_commit(int(nuevo.id)) is False


def test_distrito_despues_de_geocode_ok(app_ctx, monkeypatch):
    """H: distrito se resuelve tras geocode OK en worker."""
    app_ctx.config["GEOCODER_PROVIDER"] = "geoapify"
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocoding.services.geocode_service.get_geocoder_provider",
        lambda: "geoapify",
    )
    dist = db.session.execute(db.text("SELECT id FROM distrito ORDER BY id ASC LIMIT 1")).scalar()
    if dist is None:
        pytest.skip("Sin distritos en BD")

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.pipeline_service.normalizar_domicilio",
        _mock_normalizar_domicilio_ok,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocoding.services.geocode_service._request_geoapify",
        lambda _q: {
            "features": [
                {
                    "geometry": {"coordinates": [-65.233452, -26.8166506]},
                    "properties": {
                        "rank": {"confidence": 0.99},
                        "housenumber": "2500",
                        "result_type": "building",
                    },
                }
            ]
        },
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.distritos_service.resolve_distrito_id",
        lambda _lat, _lng: dist,
    )

    rel = crear_relevamiento_desde_payload(_mk_payload(calle=uniq("DistGeo"), numero="2500"))
    domicilio_id = int(rel.domicilio_id)
    schedule_geocode_after_grid_commit([domicilio_id])

    dom = db.session.get(Domicilio, domicilio_id)
    geo = DomicilioGeocode.query.filter_by(domicilio_id=domicilio_id).first()
    assert dom is not None
    assert geo is not None
    assert str(geo.geo_status) == "OK"
    assert dom.distrito_id == dist
