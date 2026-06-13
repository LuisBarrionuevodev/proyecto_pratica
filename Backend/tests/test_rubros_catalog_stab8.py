"""
STAB-8 — catálogo unificado de rubros desde DB.
"""

from __future__ import annotations

import random
from uuid import uuid4

import pytest

from app.database import db
from app.domains.catalogos.services.rubros_catalog_service import listar_rubros_catalogo
from app.models import Rubro


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_rubro(nombre: str) -> Rubro:
    r = Rubro(nombre=nombre)
    db.session.add(r)
    db.session.flush()
    return r


def test_listar_rubros_ordenados_por_nombre(app_ctx) -> None:
    try:
        suf = uuid4().hex[:6]
        _mk_rubro(f"ZZZ Stab8 {suf}")
        _mk_rubro(f"AAA Stab8 {suf}")
        items = listar_rubros_catalogo(q=f"Stab8 {suf}", limit=50)
        nombres = [i["nombre"] for i in items]
        assert nombres == sorted(nombres, key=lambda x: x.lower())
        assert all("id" in i and "nombre" in i and i.get("activo") is True for i in items)
    finally:
        db.session.rollback()


def test_listar_rubros_respeta_limit(app_ctx) -> None:
    try:
        items = listar_rubros_catalogo(limit=3)
        assert len(items) <= 3
    finally:
        db.session.rollback()


def test_catalogos_route_busqueda(client) -> None:
    suf = f"UniqRub{random.randint(1000, 9999)}"
    from app import create_app

    app = create_app()
    with app.app_context():
        try:
            _mk_rubro(suf)
            db.session.commit()
            resp = client.get(f"/catalogos/rubros?q={suf}&limit=10")
            assert resp.status_code == 200
            data = resp.get_json()
            assert "items" in data
            assert any(suf in it["nombre"] for it in data["items"])
            assert all(len(it.keys()) <= 4 for it in data["items"])
        finally:
            db.session.rollback()


def test_grid_catalogs_rubros_compat(client, auth_headers) -> None:
    resp = client.get("/grid/catalogs/rubros", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    if data["items"]:
        assert "id" in data["items"][0]
        assert "nombre" in data["items"][0]
