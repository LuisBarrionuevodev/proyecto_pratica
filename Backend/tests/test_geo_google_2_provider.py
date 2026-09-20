"""
GEO-GOOGLE.2 — adapter Google productivo, reglas de aceptación y fallback.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.database import db
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    compute_addr_hash,
    on_domicilio_changed,
)
from app.domains.geolocalizacion.geocoding.services.geocode_service import (
    geocode_domicilio,
    get_geocoder_provider,
)
from app.domains.geolocalizacion.geocoding.services.geocode_confidence import (
    google_precision_to_display_score,
    is_trusted_auto_geocode,
)
from app.domains.geolocalizacion.geocode.services.gestion_domicilios_status import (
    requiere_accion,
    resolve_status_operativo,
)
from app.domains.geolocalizacion.geocode.services.map_service import list_pendientes
from app.domains.geolocalizacion.geocoding.services.google_geocode_adapter import (
    GeocodeResult,
    build_google_queries,
    evaluate_google_geo_status,
    geocode_google_for_domicilio,
    google_can_attempt,
    normalized_to_geocode_result,
)
from app.models import Domicilio, DomicilioGeocode


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app


def _google_normalized(
    *,
    location_type: str = "ROOFTOP",
    partial_match: bool = False,
    status: str = "OK",
    lat: float = -26.823,
    lng: float = -65.203,
    place_id: str = "ChIJ_test",
) -> dict:
    return {
        "provider": "google",
        "lat": lat,
        "lng": lng,
        "place_id": place_id,
        "formatted_address": "Test Address",
        "location_type": location_type,
        "partial_match": partial_match,
        "status": status,
        "query": "q",
        "raw": {"status": status},
    }


def _mk_dom_numero(**kwargs) -> Domicilio:
    defaults = {
        "calle": "Corrientes",
        "numero": "500",
        "calle_norm_status": "OK",
        "calle_normalizada": "Corrientes",
        "numero_tipo": "NUMERO",
    }
    defaults.update(kwargs)
    dom = Domicilio(**defaults)
    db.session.add(dom)
    db.session.flush()
    return dom


def _mk_dom_esquina(**kwargs) -> Domicilio:
    defaults = {
        "calle": "Mendoza",
        "numero": "S/N",
        "calle_norm_status": "OK",
        "calle_normalizada": "Mendoza",
        "numero_tipo": "ESQUINA",
        "esquina_norm_status": "OK",
        "esquina_normalizada": "Lamadrid",
    }
    defaults.update(kwargs)
    dom = Domicilio(**defaults)
    db.session.add(dom)
    db.session.flush()
    return dom


def test_provider_google_runtime(app_ctx, monkeypatch):
    app_ctx.config["GEOCODER_PROVIDER"] = "google"
    monkeypatch.delenv("GEOCODER_PROVIDER", raising=False)
    assert get_geocoder_provider() == "google"


def test_evaluate_numero_rooftop_ok():
    assert evaluate_google_geo_status("NUMERO", "ROOFTOP", False) == "OK"


def test_evaluate_esquina_geometric_center_ok():
    assert evaluate_google_geo_status("ESQUINA", "GEOMETRIC_CENTER", False) == "OK"


def test_evaluate_partial_match_ok():
    assert evaluate_google_geo_status("NUMERO", "ROOFTOP", True) == "OK"


def test_evaluate_approximate_ok():
    assert evaluate_google_geo_status("NUMERO", "APPROXIMATE", False) == "OK"


@pytest.mark.parametrize(
    "location_type",
    ["ROOFTOP", "RANGE_INTERPOLATED", "GEOMETRIC_CENTER", "APPROXIMATE"],
)
def test_normalized_google_coords_always_ok(location_type):
    result = normalized_to_geocode_result(
        _google_normalized(location_type=location_type, partial_match=True),
        numero_tipo="NUMERO",
        query_used="q",
    )
    assert result.geo_status == "OK"
    assert result.lat is not None
    assert result.lng is not None


def _google_geo(
    *,
    quality: str = "ROOFTOP",
    score: float = 1.0,
    geo_status: str = "OK",
) -> DomicilioGeocode:
    return DomicilioGeocode(
        domicilio_id=1,
        geo_status=geo_status,
        provider="google",
        quality=quality,
        score=score,
        lat=-26.82,
        lng=-65.20,
        source="AUTO",
    )


@pytest.mark.parametrize(
    "quality,score",
    [
        ("ROOFTOP", 1.0),
        ("INTERPOLATED", 0.92),
        ("GEOMETRIC_CENTER", 0.90),
        ("APPROXIMATE", 0.70),
    ],
)
def test_google_precision_geolocalizado_not_requiere_accion(quality, score):
    geo = _google_geo(quality=quality, score=score)
    assert is_trusted_auto_geocode(geo) is True
    status = resolve_status_operativo(None, geo)
    assert status == "geolocalizado"
    assert requiere_accion(status) is False


def test_google_zero_results_requiere_accion():
    result = normalized_to_geocode_result(
        _google_normalized(status="ZERO_RESULTS", lat=None, lng=None),
        numero_tipo="NUMERO",
        query_used="q",
    )
    assert result.geo_status == "NO_MATCH"
    geo = DomicilioGeocode(
        domicilio_id=1,
        geo_status="NO_MATCH",
        provider="google",
        source="AUTO",
    )
    assert resolve_status_operativo(None, geo) == "error"
    assert requiere_accion("error") is True


def test_google_error_requiere_accion():
    geo = DomicilioGeocode(
        domicilio_id=1,
        geo_status="ERROR",
        provider="google",
        source="AUTO",
        error_msg="REQUEST_DENIED",
    )
    assert resolve_status_operativo(None, geo) == "error"


def test_google_ok_not_in_map_pendientes(app_ctx):
    dom = _mk_dom_numero()
    db.session.add(
        DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status="OK",
            provider="google",
            quality="APPROXIMATE",
            score=0.70,
            lat=-26.823,
            lng=-65.203,
            source="AUTO",
        )
    )
    db.session.commit()

    pending_ids = {int(item["domicilio_id"]) for item in list_pendientes(kind="map")}
    assert int(dom.id) not in pending_ids


def test_google_rooftop_display_score():
    assert google_precision_to_display_score("ROOFTOP") == 1.0
    assert google_precision_to_display_score("INTERPOLATED") == 0.92


def test_google_rooftop_ok_trusted_for_gestion():
    geo = DomicilioGeocode(
        domicilio_id=1,
        geo_status="OK",
        provider="google",
        quality="ROOFTOP",
        score=1.0,
        lat=-26.82,
        lng=-65.20,
        source="AUTO",
    )
    assert is_trusted_auto_geocode(geo) is True
    assert resolve_status_operativo(None, geo) == "geolocalizado"


def test_zero_results_no_match():
    result = normalized_to_geocode_result(
        _google_normalized(status="ZERO_RESULTS", lat=None, lng=None),
        numero_tipo="NUMERO",
        query_used="q",
    )
    assert result.geo_status == "NO_MATCH"


def test_raw_fallback_query_when_catalog_fails():
    dom = Domicilio(
        calle="Calle Rara Sin Catalogo",
        numero="123",
        calle_norm_status="PENDING",
        numero_tipo="NUMERO",
    )
    queries = build_google_queries(dom)
    assert len(queries) == 1
    assert "Calle Rara Sin Catalogo 123" in queries[0]
    assert google_can_attempt(dom) is True


def test_geoapify_still_requires_normalization(app_ctx):
    dom = _mk_dom_numero(calle_norm_status="PENDING", calle_normalizada=None)
    from app.domains.geolocalizacion.geocoding.services.geocode_service import (
        _can_geocode_for_provider,
    )

    assert _can_geocode_for_provider(dom, "geoapify")[0] is False
    assert _can_geocode_for_provider(dom, "google")[0] is True


def test_geocode_numero_rooftop_ok(app_ctx, monkeypatch):
    app_ctx.config["GEOCODER_PROVIDER"] = "google"
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")

    dom = _mk_dom_numero()
    db.session.add(DomicilioGeocode(domicilio_id=dom.id, geo_status="GEO_PENDING", source="AUTO"))
    db.session.commit()

    fake = GeocodeResult(
        lat=-26.823,
        lng=-65.203,
        provider="google",
        provider_place_id="pid-1",
        precision="ROOFTOP",
        confidence=1.0,
        formatted_address="addr",
        partial_match=False,
        raw_status="OK",
        geo_status="OK",
        raw_payload={"status": "OK"},
        query_used="Corrientes 500, San Miguel de Tucumán, Tucumán, Argentina",
    )

    resolved: list[tuple[float, float]] = []

    def _resolve(lat: float, lng: float):
        resolved.append((lat, lng))
        return None

    with patch(
        "app.domains.geolocalizacion.geocoding.services.google_geocode_adapter.geocode_google_for_domicilio",
        return_value=fake,
    ), patch(
        "app.domains.geolocalizacion.geocode.services.distritos_service.resolve_distrito_id",
        side_effect=_resolve,
    ):
        result = geocode_domicilio(int(dom.id))

    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert result["ok"] is True
    assert geo.geo_status == "OK"
    assert geo.provider == "google"
    assert geo.quality == "ROOFTOP"
    assert float(geo.score) == 1.0
    assert geo.provider_place_id == "pid-1"
    assert resolved == [(-26.823, -65.203)]


def test_geocode_esquina_geometric_center_ok(app_ctx, monkeypatch):
    app_ctx.config["GEOCODER_PROVIDER"] = "google"
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    dom = _mk_dom_esquina()
    db.session.add(DomicilioGeocode(domicilio_id=dom.id, geo_status="GEO_PENDING", source="AUTO"))
    db.session.commit()

    fake = GeocodeResult(
        lat=-26.82,
        lng=-65.20,
        provider="google",
        provider_place_id="pid-esq",
        precision="GEOMETRIC_CENTER",
        confidence=0.90,
        formatted_address="addr",
        partial_match=False,
        raw_status="OK",
        geo_status="OK",
        raw_payload={"status": "OK"},
        query_used="Mendoza y Lamadrid, San Miguel de Tucumán, Tucumán, Argentina",
    )
    with patch(
        "app.domains.geolocalizacion.geocoding.services.google_geocode_adapter.geocode_google_for_domicilio",
        return_value=fake,
    ), patch(
        "app.domains.geolocalizacion.geocode.services.distritos_service.resolve_distrito_id",
        return_value=None,
    ):
        geocode_domicilio(int(dom.id))

    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert geo.geo_status == "OK"
    assert geo.quality == "GEOMETRIC_CENTER"


def test_google_fallback_to_geoapify_on_zero_results(app_ctx, monkeypatch):
    app_ctx.config["GEOCODER_PROVIDER"] = "google"
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    monkeypatch.setenv("GEOCODER_FALLBACK_PROVIDER", "geoapify")

    dom = _mk_dom_numero()
    db.session.add(DomicilioGeocode(domicilio_id=dom.id, geo_status="GEO_PENDING", source="AUTO"))
    db.session.commit()

    google_fail = GeocodeResult(
        lat=None,
        lng=None,
        provider="google",
        provider_place_id=None,
        precision=None,
        confidence=None,
        formatted_address=None,
        partial_match=None,
        raw_status="ZERO_RESULTS",
        geo_status="NO_MATCH",
        error_msg="no match",
        raw_payload=None,
        query_used="q",
    )

    with patch(
        "app.domains.geolocalizacion.geocoding.services.google_geocode_adapter.geocode_google_for_domicilio",
        return_value=google_fail,
    ), patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_service._request_geoapify",
        return_value={
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
    ), patch(
        "app.domains.geolocalizacion.geocode.services.distritos_service.resolve_distrito_id",
        return_value=None,
    ):
        geocode_domicilio(int(dom.id))

    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert geo.provider == "geoapify"
    assert geo.geo_status == "OK"


def test_manual_geocode_not_overwritten_on_hash_unchanged(app_ctx, monkeypatch):
    app_ctx.config["GEOCODER_PROVIDER"] = "google"
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")

    dom = _mk_dom_numero()
    addr_hash = compute_addr_hash(dom)
    db.session.add(
        DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status="OK",
            lat=-26.1,
            lng=-65.1,
            source="MANUAL",
            addr_hash=addr_hash,
            quality="MANUAL_EXACT",
        )
    )
    db.session.commit()

    with patch(
        "app.domains.geolocalizacion.geocoding.services.google_geocode_adapter.geocode_google_for_domicilio",
    ) as mock_google:
        result = on_domicilio_changed(int(dom.id))

    mock_google.assert_not_called()
    assert result.get("skipped") is True
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert float(geo.lat) == -26.1
    assert geo.source == "MANUAL"


def test_addr_hash_unchanged_skips_geocode(app_ctx, monkeypatch):
    app_ctx.config["GEOCODER_PROVIDER"] = "google"
    dom = _mk_dom_numero()
    addr_hash = compute_addr_hash(dom)
    db.session.add(
        DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status="OK",
            lat=-26.82,
            lng=-65.20,
            source="AUTO",
            addr_hash=addr_hash,
            provider="google",
        )
    )
    db.session.commit()

    with patch(
        "app.domains.geolocalizacion.geocoding.services.google_geocode_adapter.geocode_google_for_domicilio",
    ) as mock_google:
        result = on_domicilio_changed(int(dom.id))

    mock_google.assert_not_called()
    assert result.get("reason") == "hash_unchanged"


def test_post_commit_prepare_no_bloquea_geocode_google(app_ctx, monkeypatch):
    """Tras commit-batch, prepare + pipeline deben llamar Google (no skip hash_unchanged)."""
    from app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service import (
        prepare_geocode_state_after_commit,
    )
    from app.domains.geolocalizacion.geocode.services.pipeline_service import pipeline_post_commit

    app_ctx.config["GEOCODER_PROVIDER"] = "google"
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    monkeypatch.setenv("GEO_POST_COMMIT_ASYNC", "false")

    dom = _mk_dom_numero(calle="Mendoza", numero="2825", calle_normalizada="Mendoza")
    db.session.commit()

    prepare_geocode_state_after_commit(int(dom.id))
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert geo is not None
    assert str(geo.geo_status) == "GEO_PENDING"
    assert geo.addr_hash is None

    fake = GeocodeResult(
        lat=-26.823,
        lng=-65.203,
        provider="google",
        provider_place_id="pid-post-commit",
        precision="ROOFTOP",
        confidence=1.0,
        formatted_address="addr",
        partial_match=False,
        raw_status="OK",
        geo_status="OK",
        raw_payload={"status": "OK"},
        query_used="Mendoza 2825, San Miguel de Tucumán, Tucumán, Argentina",
    )
    with patch(
        "app.domains.geolocalizacion.geocoding.services.google_geocode_adapter.geocode_google_for_domicilio",
        return_value=fake,
    ), patch(
        "app.domains.geolocalizacion.geocode.services.distritos_service.resolve_distrito_id",
        return_value=None,
    ):
        pipeline_post_commit(int(dom.id))

    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert geo.provider == "google"
    assert geo.geo_status == "OK"
    assert geo.checked_at is not None


def test_google_key_not_in_error_msg(app_ctx, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "super-secret-key-xyz")
    dom = _mk_dom_numero()
    db.session.add(DomicilioGeocode(domicilio_id=dom.id, geo_status="GEO_PENDING", source="AUTO"))
    db.session.commit()
    app_ctx.config["GEOCODER_PROVIDER"] = "google"

    fake = GeocodeResult(
        lat=None,
        lng=None,
        provider="google",
        provider_place_id=None,
        precision=None,
        confidence=None,
        formatted_address=None,
        partial_match=None,
        raw_status="HTTP_ERROR",
        geo_status="ERROR",
        error_msg="HTTP 403",
        raw_payload=None,
        query_used="q",
    )
    with patch(
        "app.domains.geolocalizacion.geocoding.services.google_geocode_adapter.geocode_google_for_domicilio",
        return_value=fake,
    ):
        geocode_domicilio(int(dom.id))

    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).first()
    assert "super-secret-key-xyz" not in (geo.error_msg or "")
