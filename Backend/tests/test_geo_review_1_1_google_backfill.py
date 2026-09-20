"""
GEO-REVIEW.1.1 — backfill Google GEO_PENDING con coords → OK (sin llamar Google).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.database import db
from app.domains.geolocalizacion.geocode.services.google_geocode_review_backfill_service import (
    count_google_geo_pending_con_coords,
    run_google_geocode_review_status_backfill,
)
from app.models import Domicilio, DomicilioGeocode
from tests.relevamiento_test_helpers import uniq


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_dom() -> Domicilio:
    dom = Domicilio(calle=uniq("GeoReviewBackfill"), numero="200")
    db.session.add(dom)
    db.session.flush()
    return dom


def _set_geo(
    domicilio_id: int,
    *,
    provider: str = "google",
    geo_status: str = "GEO_PENDING",
    lat: Decimal | None = Decimal("-26.8230000"),
    lng: Decimal | None = Decimal("-65.2030000"),
    source: str = "AUTO",
    quality: str = "GEOMETRIC_CENTER",
    score: float = 0.90,
) -> DomicilioGeocode:
    geo = DomicilioGeocode.query.filter_by(domicilio_id=domicilio_id, deleted_at=None).first()
    if geo is None:
        geo = DomicilioGeocode(domicilio_id=domicilio_id)
        db.session.add(geo)
    geo.provider = provider
    geo.geo_status = geo_status
    geo.lat = lat
    geo.lng = lng
    geo.source = source
    geo.quality = quality
    geo.score = score
    geo.provider_place_id = "place-test"
    geo.checked_at = None
    db.session.flush()
    return geo


def test_google_geo_pending_con_coords_apply_ok(app_ctx) -> None:
    dom = _mk_dom()
    geo = _set_geo(dom.id)
    db.session.commit()

    summary = run_google_geocode_review_status_backfill(apply=True, domicilio_id=int(dom.id))
    assert summary.candidatos == 1
    assert summary.actualizados == 1
    assert summary.errores == 0

    db.session.refresh(geo)
    assert str(geo.geo_status) == "OK"
    assert geo.lat is not None
    assert geo.lng is not None
    assert geo.quality == "GEOMETRIC_CENTER"
    assert float(geo.score) == 0.90
    assert geo.provider_place_id == "place-test"


def test_google_geo_pending_sin_coords_no_cambia(app_ctx) -> None:
    dom = _mk_dom()
    _set_geo(dom.id, lat=None, lng=None)
    db.session.commit()

    summary = run_google_geocode_review_status_backfill(apply=True, domicilio_id=int(dom.id))
    assert summary.candidatos == 0
    assert summary.actualizados == 0

    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert str(geo.geo_status) == "GEO_PENDING"
    assert geo.lat is None


def test_google_no_match_no_cambia(app_ctx) -> None:
    dom = _mk_dom()
    _set_geo(dom.id, geo_status="NO_MATCH")
    db.session.commit()

    summary = run_google_geocode_review_status_backfill(apply=True, domicilio_id=int(dom.id))
    assert summary.candidatos == 0
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert str(geo.geo_status) == "NO_MATCH"


def test_google_error_no_cambia(app_ctx) -> None:
    dom = _mk_dom()
    _set_geo(dom.id, geo_status="ERROR")
    db.session.commit()

    summary = run_google_geocode_review_status_backfill(apply=True, domicilio_id=int(dom.id))
    assert summary.candidatos == 0
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert str(geo.geo_status) == "ERROR"


def test_geoapify_geo_pending_no_cambia(app_ctx) -> None:
    dom = _mk_dom()
    _set_geo(dom.id, provider="geoapify")
    db.session.commit()

    summary = run_google_geocode_review_status_backfill(apply=True, domicilio_id=int(dom.id))
    assert summary.candidatos == 0
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert str(geo.geo_status) == "GEO_PENDING"
    assert geo.provider == "geoapify"


def test_manual_no_cambia(app_ctx) -> None:
    dom = _mk_dom()
    _set_geo(dom.id, source="MANUAL")
    db.session.commit()

    summary = run_google_geocode_review_status_backfill(apply=True, domicilio_id=int(dom.id))
    assert summary.candidatos == 0
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert str(geo.geo_status) == "GEO_PENDING"
    assert str(geo.source) == "MANUAL"


def test_dry_run_no_persiste(app_ctx) -> None:
    dom = _mk_dom()
    _set_geo(dom.id)
    db.session.commit()

    summary = run_google_geocode_review_status_backfill(apply=False, domicilio_id=int(dom.id))
    assert summary.mode == "dry_run"
    assert summary.candidatos == 1
    assert summary.actualizados == 1

    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert str(geo.geo_status) == "GEO_PENDING"


def test_segunda_ejecucion_cero_cambios(app_ctx) -> None:
    dom = _mk_dom()
    _set_geo(dom.id)
    db.session.commit()

    first = run_google_geocode_review_status_backfill(apply=True, domicilio_id=int(dom.id))
    assert first.actualizados == 1

    second = run_google_geocode_review_status_backfill(apply=True, domicilio_id=int(dom.id))
    assert second.candidatos == 0
    assert second.actualizados == 0
    assert count_google_geo_pending_con_coords(domicilio_id=int(dom.id)) == 0


def test_sin_distrito_solo_reporte(app_ctx) -> None:
    dom = _mk_dom()
    dom.distrito_id = None
    _set_geo(dom.id)
    db.session.commit()

    dry = run_google_geocode_review_status_backfill(apply=False, domicilio_id=int(dom.id))
    assert dry.sin_distrito == 1

    applied = run_google_geocode_review_status_backfill(apply=True, domicilio_id=int(dom.id))
    assert applied.sin_distrito == 1
    assert dom.distrito_id is None
