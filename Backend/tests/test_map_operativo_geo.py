"""Mapa operativo: pendientes / realizados (GeoJSON)."""

from datetime import date

import pytest

from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    list_mapa_operativo_pendientes_geo,
    list_mapa_operativo_realizados_geo,
)


def test_pendientes_geo_exige_rango(app) -> None:
    with app.app_context():
        with pytest.raises(ValueError, match="obligatorios"):
            list_mapa_operativo_pendientes_geo(desde=None, hasta="2026-01-31")
        with pytest.raises(ValueError, match="obligatorios"):
            list_mapa_operativo_pendientes_geo(desde="2026-01-01", hasta=None)


def test_pendientes_geo_rango_vacio_ok(app) -> None:
    with app.app_context():
        out = list_mapa_operativo_pendientes_geo(
            desde="2099-01-01",
            hasta="2099-01-31",
            distrito_id=None,
            tipo=None,
            inspector_id=None,
        )
    assert out == []


def test_realizados_geo_rango_vacio_ok(app) -> None:
    with app.app_context():
        out = list_mapa_operativo_realizados_geo(
            desde=date(2099, 1, 1).isoformat(),
            hasta=date(2099, 1, 31).isoformat(),
        )
    assert out == []


def test_http_operativo_pendientes_sin_fechas_400(client, auth_headers) -> None:
    resp = client.get("/map/operativo/pendientes", headers=auth_headers)
    assert resp.status_code == 400


def test_http_operativo_pendientes_vacio_fc_200(client, auth_headers) -> None:
    resp = client.get(
        "/map/operativo/pendientes?desde=2099-01-01&hasta=2099-01-07",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("type") == "FeatureCollection"
    assert data.get("features") == []


def test_http_operativo_realizados_con_definicion_vacio_fc_200(client, auth_headers) -> None:
    """Filtro definición debe aceptarse sin error (sin datos en rango lejano)."""
    resp = client.get(
        "/map/operativo/realizados?desde=2099-01-01&hasta=2099-01-07&definicion=CLAUSURA",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("type") == "FeatureCollection"
    assert data.get("features") == []
