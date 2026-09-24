"""Lecturas API /establecimientos-operativos (JWT)."""

from __future__ import annotations


def test_list_requires_jwt(client) -> None:
    r = client.get("/establecimientos-operativos")
    assert r.status_code == 401


def test_list_ok_with_jwt(client, auth_headers) -> None:
    r = client.get("/establecimientos-operativos", headers=auth_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data
    assert "meta" in data
    assert data["meta"].get("total") is not None


def test_detail_404(client, auth_headers) -> None:
    r = client.get("/establecimientos-operativos/999999999", headers=auth_headers)
    assert r.status_code == 404


def test_actuaciones_404_unknown_ficha(client, auth_headers) -> None:
    r = client.get("/establecimientos-operativos/999999999/actuaciones", headers=auth_headers)
    assert r.status_code == 404
