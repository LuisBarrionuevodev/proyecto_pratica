"""V1.1-RELEVAMIENTO-ROLE.1 — perfil carga/gestión relevamientos."""

from __future__ import annotations

import random

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401 — pytest fixture
from app.domains.usuarios.security.role_permissions import (
    relevamiento_may_access,
    relevador_may_access,
    role_may_access_endpoint,
)
from app.domains.usuarios.schemas import AdminUserCreateRequest
from app.models import User


def test_schema_acepta_rol_relevamiento_sin_inspector() -> None:
    req = AdminUserCreateRequest.model_validate(
        {
            "username": "rel_data",
            "email": "rel_data@example.com",
            "password": "secret12",
            "role": "relevamiento",
        }
    )
    assert req.role == "relevamiento"
    assert req.inspector_id is None


def test_relevamiento_allowlist_relevamientos_y_perfil() -> None:
    assert relevamiento_may_access("GET", "/relevamientos")
    assert relevamiento_may_access("GET", "/relevamientos/gestion-operativa")
    assert relevamiento_may_access("GET", "/relevamientos/realizados")
    assert relevamiento_may_access("GET", "/relevamientos/pendientes/summary")
    assert relevamiento_may_access("POST", "/relevamientos")
    assert relevamiento_may_access("PUT", "/relevamientos/9")
    assert relevamiento_may_access("DELETE", "/relevamientos/9")
    assert relevamiento_may_access("GET", "/api/profile/me")
    assert relevamiento_may_access("GET", "/catalogos/rubros")
    assert relevamiento_may_access("GET", "/grid/catalogs/relevadores")


def test_relevamiento_bloquea_modulos_operativos() -> None:
    assert not relevamiento_may_access("GET", "/actuaciones")
    assert not relevamiento_may_access("GET", "/actuaciones/completar-trabajo/pendientes")
    assert not relevamiento_may_access("GET", "/rutas-trabajo/1/planificacion/metricas")
    assert not relevamiento_may_access("GET", "/api/indicadores/ejecutivo")
    assert not relevamiento_may_access("GET", "/map/operativo/pendientes")
    assert not relevamiento_may_access("GET", "/api/admin/users")
    assert not relevamiento_may_access("GET", "/api/denuncias/gestion")
    assert not relevamiento_may_access("POST", "/api/denuncias")
    assert not relevamiento_may_access("GET", "/grid/catalogs/inspectores")


def test_relevamiento_grid_solo_kind_relevamientos() -> None:
    from flask import Flask

    app = Flask(__name__)
    with app.test_request_context(
        "/grid/start",
        method="POST",
        json={"kind": "relevamientos"},
    ):
        assert relevamiento_may_access("POST", "/grid/start")
    with app.test_request_context(
        "/grid/start",
        method="POST",
        json={"kind": "actuaciones"},
    ):
        assert not relevamiento_may_access("POST", "/grid/start")
    with app.test_request_context("/grid/start", method="POST", json={}):
        assert not relevamiento_may_access("POST", "/grid/start")


def test_relevador_inspector_sin_cambios() -> None:
    assert relevador_may_access("GET", "/actuaciones")
    assert not relevador_may_access("GET", "/relevamientos")
    assert role_may_access_endpoint("usuario", "GET", "/relevamientos")


def _create_relevamiento_user() -> User:
    suf = f"{random.randint(0, 999999):06d}"
    u = User(
        username=f"relm_{suf}",
        email=f"relm_{suf}@example.com",
        password_hash="x",
        role="relevamiento",
        is_active=True,
    )
    db.session.add(u)
    db.session.commit()
    return u


def test_http_relevamiento_403_actuaciones_y_admin(app, client, scope_fixture) -> None:
    user = _create_relevamiento_user()
    assert user.role == "relevamiento"
    token = create_access_token(identity=str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    cases = (
        ("POST", "/actuaciones", {}),
        ("GET", "/api/admin/users", None),
        ("GET", "/rutas-trabajo/1/planificacion/metricas", None),
    )
    for method, path, body in cases:
        resp = client.open(path, method=method, headers=headers, json=body)
        assert resp.status_code == 403
        assert resp.get_json()["detail"] == "No tiene permisos para esta acción"


def test_http_relevamiento_200_perfil_y_listado(app, client, scope_fixture) -> None:
    user = _create_relevamiento_user()
    token = create_access_token(identity=str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/profile/me", headers=headers)
    assert me.status_code == 200
    lista = client.get("/relevamientos", headers=headers)
    assert lista.status_code == 200
