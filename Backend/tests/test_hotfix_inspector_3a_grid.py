"""HOTFIX V1.1-INSPECTOR.3A — relevador sin Grid masivo; solo catálogos GET."""

from __future__ import annotations

import random

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.usuarios.security.passwords import hash_password
from app.domains.usuarios.security.role_permissions import relevador_may_access, role_may_access_endpoint
from app.models import Inspector, Turno, User
from app.models.turno import TipoTurno

GRID_MASSIVE_ENDPOINTS: tuple[tuple[str, str], ...] = (
    ("POST", "/grid/start"),
    ("POST", "/grid/validate-row"),
    ("POST", "/grid/validate-batch"),
    ("POST", "/grid/commit-row"),
    ("POST", "/grid/commit-batch"),
)

GRID_CATALOG_GET_PATHS: tuple[str, ...] = (
    "/grid/catalogs/inspectores",
    "/grid/catalogs/motivos",
    "/grid/catalogs/contraproducencias",
    "/grid/catalogs/motivos-comprobacion",
    "/grid/catalogs/items-acta-inspeccion",
    "/catalogos/rubros",
)


def test_relevador_denies_grid_massive_unit() -> None:
    for method, path in GRID_MASSIVE_ENDPOINTS:
        assert not relevador_may_access(method, path)


def test_relevador_allows_grid_catalogs_get_unit() -> None:
    for path in GRID_CATALOG_GET_PATHS:
        assert relevador_may_access("GET", path)


def test_relevador_denies_other_grid_paths() -> None:
    assert not relevador_may_access("GET", "/grid/catalogs/tipos")
    assert not relevador_may_access("GET", "/grid/catalogs/rubros")
    assert not relevador_may_access("GET", "/grid/catalogs/juzgados")
    assert not relevador_may_access("POST", "/grid/catalogs/motivos")


def test_admin_usuario_grid_massive_unrestricted() -> None:
    for method, path in GRID_MASSIVE_ENDPOINTS:
        assert role_may_access_endpoint("admin", method, path)
        assert role_may_access_endpoint("usuario", method, path)


@pytest.fixture
def relevador_jwt_headers(app):
    with app.app_context():
        turno = Turno.query.first()
        if turno is None:
            turno = Turno(turno=TipoTurno.MANIANA)
            db.session.add(turno)
            db.session.flush()
        suf = f"{random.randint(0, 999999):06d}"
        ins = Inspector(nombre=f"Insp {suf}", legajo=suf[:5], turno_id=turno.id)
        db.session.add(ins)
        db.session.flush()
        user = User(
            username=f"rel_{suf}",
            email=f"rel_{suf}@t.local",
            password_hash=hash_password("x"),
            role="relevador",
            is_active=True,
            inspector_id=ins.id,
        )
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=str(user.id))
        yield {"Authorization": f"Bearer {token}"}
        db.session.rollback()


def test_relevador_http_403_grid_massive(client, relevador_jwt_headers) -> None:
    headers = relevador_jwt_headers
    for method, path in GRID_MASSIVE_ENDPOINTS:
        assert method == "POST"
        resp = client.post(path, headers=headers, json={})
        assert resp.status_code == 403
        assert resp.get_json()["detail"] == "No tiene permisos para esta acción"
        assert resp.get_json()["detail"] == "No tiene permisos para esta acción"


def test_relevador_http_200_grid_catalogs(client, relevador_jwt_headers) -> None:
    headers = relevador_jwt_headers
    for path in GRID_CATALOG_GET_PATHS:
        resp = client.get(path, headers=headers)
        assert resp.status_code == 200


def test_admin_http_grid_start_not_forbidden_by_role(client, app):
    with app.app_context():
        suf = f"{random.randint(0, 999999):06d}"
        admin = User(
            username=f"adm_{suf}",
            email=f"adm_{suf}@t.local",
            password_hash=hash_password("x"),
            role="admin",
            is_active=True,
        )
        db.session.add(admin)
        db.session.commit()
        token = create_access_token(identity=str(admin.id))
        headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/grid/start", headers=headers, json={})
    assert resp.status_code != 403
