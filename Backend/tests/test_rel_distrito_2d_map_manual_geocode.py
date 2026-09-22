"""
REL-DISTRITO.2D — distrito persistido tras POST /api/map/geocode/manual.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.relevamiento_iniciador_service import (
    get_or_create_iniciador_from_relevamiento,
)
from app.models import Domicilio, DomicilioGeocode, Distrito, Relevamiento
from tests.relevamiento_test_helpers import get_or_create_test_relevador, get_test_rubro, uniq

_LAT = -26.8166506
_LNG = -65.233452


def _distrito_test() -> Distrito:
    dist = Distrito.query.order_by(Distrito.id.asc()).first()
    if dist is None:
        pytest.skip("Se requiere al menos un distrito en la BD de test")
    return dist


def _mk_domicilio_sin_distrito() -> Domicilio:
    dom = Domicilio(calle=uniq("RelDist2d"), numero="2500", distrito_id=None)
    db.session.add(dom)
    db.session.flush()
    return dom


def _patch_resolve(monkeypatch: pytest.MonkeyPatch, resolver) -> None:
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.map_service.resolve_distrito_id",
        resolver,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.distrito_backfill_service.resolve_distrito_id",
        resolver,
    )


def _post_manual_geocode(client, auth_headers, domicilio_id: int) -> int:
    resp = client.post(
        "/api/map/geocode/manual",
        headers=auth_headers,
        json={"domicilio_id": domicilio_id, "lat": _LAT, "lng": _LNG},
    )
    assert resp.status_code == 200
    return resp.status_code


def _mk_relevamiento_operativo(domicilio_id: int) -> Relevamiento:
    rev = get_or_create_test_relevador()
    rub = get_test_rubro()
    rel = crear_relevamiento_desde_payload(
        {
            "fecha": date.today().isoformat(),
            "relevadores_nombres": [rev.nombre],
            "domicilio": {"calle": uniq("RelDist2dRel"), "numero": "1"},
            "rubro_nombre": rub.nombre,
        }
    )
    dom = db.session.get(Domicilio, rel.domicilio_id)
    assert dom is not None
    rel.domicilio_id = int(domicilio_id)
    dom = db.session.get(Domicilio, domicilio_id)
    assert dom is not None
    dom.distrito_id = None
    ini = get_or_create_iniciador_from_relevamiento(rel, actor_user_id=1)
    ini.estado_iniciador = "PENDIENTE"
    db.session.add_all([rel, dom, ini])
    db.session.commit()
    return rel


def test_post_manual_geocode_persiste_distrito(
    client, auth_headers, app_ctx, monkeypatch
) -> None:
    dist = _distrito_test()
    _patch_resolve(monkeypatch, lambda _lat, _lng: dist.id)
    dom = _mk_domicilio_sin_distrito()
    db.session.commit()

    _post_manual_geocode(client, auth_headers, int(dom.id))

    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id, deleted_at=None).first()
    dom_ref = db.session.get(Domicilio, dom.id)
    assert geo is not None
    assert geo.geo_status == "OK"
    assert float(geo.lat) == _LAT
    assert float(geo.lng) == _LNG
    assert str(geo.source) == "MANUAL"
    assert dom_ref is not None
    assert dom_ref.distrito_id == dist.id


def test_gestion_operativa_muestra_distrito_tras_manual_geocode(
    client, auth_headers, app_ctx, monkeypatch
) -> None:
    dist = _distrito_test()
    _patch_resolve(monkeypatch, lambda _lat, _lng: dist.id)
    dom = _mk_domicilio_sin_distrito()
    rel = _mk_relevamiento_operativo(int(dom.id))

    _post_manual_geocode(client, auth_headers, int(dom.id))

    resp = client.get(
        "/relevamientos/gestion-operativa",
        headers=auth_headers,
        query_string={
            "desde": "2020-01-01",
            "hasta": "2099-12-31",
            "page": 1,
            "page_size": 500,
        },
    )
    assert resp.status_code == 200
    items = resp.get_json()["items"]
    row = next((item for item in items if int(item["id"]) == int(rel.id)), None)
    assert row is not None
    assert row["distrito_id"] == dist.id
    expected_mostrar = dist.nombre or f"Distrito {dist.codigo}"
    assert row["distrito_mostrar"] == expected_mostrar


def test_post_manual_geocode_distrito_error_no_rompe_geocode(
    client, auth_headers, app_ctx, monkeypatch
) -> None:
    def _boom(_lat, _lng):
        raise RuntimeError("fallo resolver")

    _patch_resolve(monkeypatch, _boom)
    dom = _mk_domicilio_sin_distrito()
    db.session.commit()

    _post_manual_geocode(client, auth_headers, int(dom.id))

    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id, deleted_at=None).first()
    dom_ref = db.session.get(Domicilio, dom.id)
    assert geo is not None
    assert geo.geo_status == "OK"
    assert float(geo.lat) == _LAT
    assert float(geo.lng) == _LNG
    assert dom_ref is not None
    assert dom_ref.distrito_id is None


def test_post_manual_geocode_distrito_no_match_sin_error(
    client, auth_headers, app_ctx, monkeypatch
) -> None:
    _patch_resolve(monkeypatch, lambda _lat, _lng: None)
    dom = _mk_domicilio_sin_distrito()
    db.session.commit()

    _post_manual_geocode(client, auth_headers, int(dom.id))

    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id, deleted_at=None).first()
    dom_ref = db.session.get(Domicilio, dom.id)
    assert geo is not None
    assert geo.geo_status == "OK"
    assert dom_ref is not None
    assert dom_ref.distrito_id is None


def test_post_manual_geocode_backfill_recupera_distrito(
    client, auth_headers, app_ctx, monkeypatch
) -> None:
    dist = _distrito_test()
    calls = {"n": 0}

    def _resolve_once_fail_then_ok(_lat, _lng):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("fallo inicial")
        return dist.id

    _patch_resolve(monkeypatch, _resolve_once_fail_then_ok)
    dom = _mk_domicilio_sin_distrito()
    db.session.commit()

    _post_manual_geocode(client, auth_headers, int(dom.id))

    dom_ref = db.session.get(Domicilio, dom.id)
    geo = DomicilioGeocode.query.filter_by(domicilio_id=dom.id, deleted_at=None).first()
    assert geo is not None
    assert geo.geo_status == "OK"
    assert dom_ref is not None
    assert dom_ref.distrito_id == dist.id
    assert calls["n"] >= 2
