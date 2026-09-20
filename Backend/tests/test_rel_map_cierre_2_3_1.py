"""
REL-MAP-CIERRE.2-3.1 — rubro opcional + geocode GEO-PERF async en edit PUT.
"""

from __future__ import annotations

from datetime import date
import pytest
from sqlalchemy import inspect

from app.database import db
from app.domains.grid.services.batch_store import InMemoryBatchStore
from app.domains.grid.services.validate_service import GridValidateService
from app.domains.relevamientos.mappers.grid.relevamiento_row_mapper import map_relevamiento_row
from app.domains.relevamientos.schemas.grid.relevamiento_row_in import RelevamientoGridRowIn
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.update_service import actualizar_relevamiento
from app.models import DomicilioGeocode, GeocodePostCommitJob, Relevamiento, Rubro
from tests.relevamiento_test_helpers import (
    get_or_create_test_relevador,
    get_test_rubro,
    relevamiento_create_payload,
    require_relevadores_migration,
    uniq,
)


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


@pytest.fixture
def require_rel_migration(app_ctx):
    require_relevadores_migration()


def _update_payload(
    *,
    calle: str,
    numero: str,
    relevador_id: int,
    rubro: str | None = None,
    turno: str | None = None,
    nombre_fantasia: str | None = None,
    esta_abierto: bool | None = None,
    angulo_esquina: str | None = None,
    numero_tipo: str | None = None,
) -> dict:
    row = RelevamientoGridRowIn.model_validate(
        {
            "calle": calle,
            "numero": numero,
            "relevador_ids": [relevador_id],
            "rubro": rubro,
            "turno": turno,
            "nombre_fantasia": nombre_fantasia,
            "esta_abierto": esta_abierto,
            "angulo_esquina": angulo_esquina,
            "numero_tipo": numero_tipo,
        },
        context={"allow_missing_relevador": True},
    )
    return map_relevamiento_row(row)


def test_put_opcionales_vacios_ok_rubro_id_null(require_rel_migration, app_ctx) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    calle = uniq("OptVac")
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=calle,
            numero="100",
            rubro=rub.nombre,
            relevador_nombre=rel.nombre,
        )
    )
    updated = actualizar_relevamiento(
        created.id,
        _update_payload(
            calle=calle,
            numero="100",
            relevador_id=rel.id,
            rubro=None,
            turno=None,
            nombre_fantasia=None,
            esta_abierto=None,
        ),
    )
    assert updated.rubro_id is None
    assert updated.turno_carga is None
    assert updated.nombre_fantasia is None
    assert updated.esta_abierto is None


def test_create_con_rubro_vacio_permitido(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    calle = uniq("CreateNoRub")
    created = crear_relevamiento_desde_payload(
        {
            "relevadores_nombres": [rel.nombre],
            "domicilio": {"calle": calle, "numero": "200"},
            "rubro_nombre": None,
            "fecha": date.today().isoformat(),
        }
    )
    assert created.rubro_id is None


def test_schema_rubro_vacio_no_error(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    row = RelevamientoGridRowIn.model_validate(
        {
            "relevador_ids": [rel.id],
            "calle": "Ayacucho",
            "numero": "Piedras",
            "rubro": "",
            "numero_tipo": "ESQUINA",
            "angulo_esquina": "",
        }
    )
    assert row.rubro is None
    assert row.angulo_esquina is None


def test_validate_row_rubro_vacio_no_500(require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    svc = GridValidateService(store)
    resp = svc.validate_row(
        batch_id,
        "r-empty-rubro",
        {
            "Relevador": rel.nombre,
            "Calle": uniq("ValRub"),
            "Numero": "10",
            "Rubro": "",
        },
        "relevamientos",
    )
    assert resp.ok is True


def test_edit_cambio_esquina_encola_geocode_post_commit(require_rel_migration, app_ctx, monkeypatch) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    calle = uniq("Ayacucho")
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=calle,
            numero="Piedras",
            rubro=rub.nombre,
            relevador_nombre=rel.nombre,
            domicilio={"calle": calle, "numero": "Piedras", "numero_tipo": "ESQUINA"},
        )
    )
    rel_id = int(created.id)
    old_dom_id = int(created.domicilio_id)
    scheduled: list[list[int]] = []

    def _capture(ids):
        scheduled.append(list(ids))
        from app.domains.grid.services.post_commit_geocode import schedule_geocode_after_grid_commit as real

        return real(ids)

    monkeypatch.setattr(
        "app.domains.relevamientos.services.update_service.schedule_geocode_after_grid_commit",
        _capture,
    )

    actualizar_relevamiento(
        rel_id,
        _update_payload(
            calle=calle,
            numero="Congreso",
            relevador_id=rel.id,
            rubro=rub.nombre,
            numero_tipo="ESQUINA",
        ),
    )
    updated = db.session.get(Relevamiento, rel_id)
    assert updated is not None
    new_dom_id = int(updated.domicilio_id)
    assert scheduled == [[new_dom_id]]
    job = GeocodePostCommitJob.query.filter_by(domicilio_id=new_dom_id).first()
    assert job is not None
    if old_dom_id != new_dom_id:
        old_job = GeocodePostCommitJob.query.filter_by(domicilio_id=old_dom_id).count()
        assert old_job == 0


def test_edit_solo_rubro_no_encola_geocode(require_rel_migration, monkeypatch) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    otro = Rubro.query.filter(Rubro.id != rub.id).first()
    calle = uniq("NoGeo")
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=calle,
            numero="50",
            rubro=rub.nombre,
            relevador_nombre=rel.nombre,
        )
    )
    dom = db.session.get(Relevamiento, created.id).domicilio
    assert dom is not None
    calls: list[list[int]] = []

    def _track(ids):
        calls.append(list(ids))
        return []

    monkeypatch.setattr(
        "app.domains.relevamientos.services.update_service.schedule_geocode_after_grid_commit",
        _track,
    )
    actualizar_relevamiento(
        int(created.id),
        _update_payload(
            calle=dom.calle,
            numero=dom.numero,
            relevador_id=rel.id,
            rubro=None,
            turno="TARDE",
        ),
    )
    assert calls == []


def test_edit_geo_pipeline_google_ok(require_rel_migration, app_ctx, monkeypatch) -> None:
    app_ctx.config["GEOCODER_PROVIDER"] = "google"
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")

    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    calle = uniq("AyacuchoGeo")
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=calle,
            numero="Piedras",
            rubro=rub.nombre,
            relevador_nombre=rel.nombre,
            domicilio={"calle": calle, "numero": "Piedras", "numero_tipo": "ESQUINA"},
        )
    )

    rel_id = int(created.id)

    def _pipeline_ok(domicilio_id: int):
        geo = DomicilioGeocode.query.filter_by(domicilio_id=int(domicilio_id)).first()
        if geo is None:
            geo = DomicilioGeocode(domicilio_id=int(domicilio_id))
        geo.geo_status = "OK"
        geo.lat = -26.852
        geo.lng = -65.203
        geo.provider = "google"
        db.session.add(geo)
        db.session.commit()
        return {"domicilio_id": domicilio_id, "geo_status": "OK"}

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service.pipeline_post_commit",
        _pipeline_ok,
    )

    actualizar_relevamiento(
        rel_id,
        _update_payload(
            calle=calle,
            numero="Congreso",
            relevador_id=rel.id,
            rubro=rub.nombre,
            numero_tipo="ESQUINA",
        ),
    )
    ref = db.session.get(Relevamiento, rel_id)
    assert ref is not None
    dom_id = int(ref.domicilio_id)
    job = GeocodePostCommitJob.query.filter_by(domicilio_id=dom_id).first()
    assert job is not None

    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom_id).first()
    assert geo is not None
    assert str(geo.geo_status) == "OK"
    assert geo.lat is not None
    assert geo.lng is not None
    assert geo.provider == "google"


def test_schedule_error_no_rollbackea_update(require_rel_migration, monkeypatch) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    calle = uniq("SchedErr")
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=calle,
            numero="10",
            rubro=rub.nombre,
            relevador_nombre=rel.nombre,
        )
    )

    def _boom(_ids):
        raise RuntimeError("enqueue failed")

    monkeypatch.setattr(
        "app.domains.relevamientos.services.update_service.schedule_geocode_after_grid_commit",
        _boom,
    )
    nueva = uniq("SchedErrNew")
    updated = actualizar_relevamiento(
        created.id,
        _update_payload(
            calle=nueva,
            numero="99",
            relevador_id=rel.id,
            rubro=rub.nombre,
        ),
    )
    assert updated.domicilio.calle == nueva
    ref = db.session.get(Relevamiento, created.id)
    assert ref is not None
    assert ref.domicilio.calle == nueva


def test_no_llama_on_domicilio_changed_sync(require_rel_migration, monkeypatch) -> None:
    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    calle = uniq("NoSync")
    created = crear_relevamiento_desde_payload(
        relevamiento_create_payload(
            calle=calle,
            numero="1",
            rubro=rub.nombre,
            relevador_nombre=rel.nombre,
        )
    )
    sync_calls: list[int] = []

    def _sync(_dom_id):
        sync_calls.append(int(_dom_id))
        return {}

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed",
        _sync,
    )
    scheduled: list[list[int]] = []

    def _sched(ids):
        scheduled.append(list(ids))
        return []

    monkeypatch.setattr(
        "app.domains.relevamientos.services.update_service.schedule_geocode_after_grid_commit",
        _sched,
    )
    actualizar_relevamiento(
        created.id,
        _update_payload(
            calle=uniq("NoSyncNew"),
            numero="2",
            relevador_id=rel.id,
            rubro=rub.nombre,
        ),
    )
    assert sync_calls == []
    assert len(scheduled) == 1
