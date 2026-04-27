"""Validación de parámetros del proxy de mapa estático OSM (PDF resumen de ruta)."""

from app.domains.geolocalizacion.geocode.services.osm_static_map_proxy_service import (
    normalize_osm_center,
    normalize_osm_markers,
)


def test_normalize_osm_center_redondea():
    assert normalize_osm_center("-26.822012800000003,-65.21187125") == "-26.82201,-65.21187"


def test_normalize_osm_markers_acota_y_redondea():
    raw = "-26.8186526,-65.2224545,red-pushpin|-26.8170523,-65.230448,red-pushpin"
    assert normalize_osm_markers(raw, max_segments=1) == "-26.81865,-65.22245,red-pushpin"


def test_map_osm_static_center_invalido_400(client, auth_headers):
    resp = client.get("/map/osm-static?center=foo&zoom=13&size=520x280", headers=auth_headers)
    assert resp.status_code == 400
    assert "center" in (resp.get_json() or {}).get("detail", "").lower()


def test_map_osm_static_zoom_fuera_rango_400(client, auth_headers):
    resp = client.get(
        "/map/osm-static?center=-26.8,-65.2&zoom=99&size=520x280",
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_map_osm_static_size_invalido_400(client, auth_headers):
    resp = client.get(
        "/map/osm-static?center=-26.8,-65.2&zoom=13&size=9999x9999",
        headers=auth_headers,
    )
    assert resp.status_code == 400
