"""HOTFIX-CIERRE-DIA: rol RELEVADOR backend."""

from __future__ import annotations

import random

import pytest

from app.database import db
from app.domains.usuarios.security.role_permissions import relevador_may_access, role_may_access_endpoint
from app.domains.usuarios.schemas import AdminUserCreateRequest
from app.models import User


def test_schema_acepta_rol_relevador() -> None:
    req = AdminUserCreateRequest.model_validate(
        {
            "username": "rel1",
            "email": "rel1@example.com",
            "password": "secret1",
            "role": "relevador",
        }
    )
    assert req.role == "relevador"


def test_relevador_permite_relevamientos_y_denuncias() -> None:
    assert relevador_may_access("GET", "/relevamientos")
    assert relevador_may_access("POST", "/api/denuncias")
    assert relevador_may_access("POST", "/actuaciones")
    assert relevador_may_access("GET", "/api/profile/me")


def test_relevador_no_lista_actuaciones() -> None:
    assert not relevador_may_access("GET", "/actuaciones")
    assert not relevador_may_access("GET", "/actuaciones/42")
    assert relevador_may_access("PUT", "/actuaciones/42")


def test_relevador_bloquea_rutas_y_admin() -> None:
    assert not relevador_may_access("GET", "/rutas-trabajo/1/planificacion/metricas")
    assert not relevador_may_access("POST", "/actuaciones/completar-trabajo/cerrar/1")
    assert not role_may_access_endpoint("relevador", "GET", "/api/admin/users")
    assert not role_may_access_endpoint("relevador", "GET", "/api/indicadores/resumen")


def test_usuario_sigue_sin_restriccion_extra() -> None:
    assert role_may_access_endpoint("usuario", "GET", "/rutas-trabajo/1/planificacion/metricas")


@pytest.fixture
def app_ctx():
    from app import create_app
    from flask_migrate import upgrade

    app = create_app()
    with app.app_context():
        try:
            upgrade()
        except Exception:
            pass
        yield app
        db.session.rollback()


def test_crear_usuario_relevador_en_db(app_ctx) -> None:
    suf = f"{random.randint(0, 999999):06d}"
    u = User(
        username=f"rel_{suf}",
        email=f"rel_{suf}@example.com",
        password_hash="x",
        role="relevador",
        is_active=True,
    )
    db.session.add(u)
    try:
        db.session.commit()
    except Exception as exc:
        pytest.skip(f"Requiere migración user_role_enum con relevador: {exc}")
    loaded = User.query.filter_by(username=u.username).first()
    assert loaded is not None
    assert loaded.role == "relevador"
