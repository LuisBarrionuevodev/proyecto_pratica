"""
PREDEPLOY-FIX.2 — regresión eliminación fallback silencioso a user id=1.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from flask_jwt_extended import create_access_token, verify_jwt_in_request

from app.domains.rutas_trabajo.services.auth_service import (
    get_current_user_id,
    validate_actor_user_id,
)
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    sync_iniciadores_reinspeccion_notificacion,
)
from app.models import User


def _patch_today_unused():
    pass


def test_get_current_user_id_jwt_non_admin(app, actor_user_id):
    with app.app_context():
        non_admin = (
            User.query.filter(User.is_active.is_(True), User.id != actor_user_id)
            .order_by(User.id.asc())
            .first()
        )
        assert non_admin is not None
        token = create_access_token(identity=str(non_admin.id))
        with app.test_request_context(
            "/", headers={"Authorization": f"Bearer {token}"}
        ):
            verify_jwt_in_request()
            assert get_current_user_id() == int(non_admin.id)


def test_get_current_user_id_jwt_admin_id1(app, actor_user_id):
    with app.app_context():
        token = create_access_token(identity=str(actor_user_id))
        with app.test_request_context(
            "/", headers={"Authorization": f"Bearer {token}"}
        ):
            verify_jwt_in_request()
            assert get_current_user_id() == actor_user_id


def test_get_current_user_id_request_without_jwt_raises(app):
    with app.app_context():
        with app.test_request_context("/"):
            with pytest.raises(ValueError, match="Usuario no autorizado"):
                get_current_user_id()


def test_get_current_user_id_no_request_context_raises():
    with pytest.raises(ValueError, match="Usuario no autorizado"):
        get_current_user_id()


def test_get_current_user_id_invalid_identity_raises(app):
    with app.app_context():
        token = create_access_token(identity="not-a-number")
        with app.test_request_context(
            "/", headers={"Authorization": f"Bearer {token}"}
        ):
            verify_jwt_in_request()
            with pytest.raises(ValueError, match="Usuario no autorizado"):
                get_current_user_id()


def test_get_current_user_id_nonexistent_user_raises(app):
    with app.app_context():
        token = create_access_token(identity="999999999")
        with app.test_request_context(
            "/", headers={"Authorization": f"Bearer {token}"}
        ):
            verify_jwt_in_request()
            with pytest.raises(ValueError, match="Usuario no autorizado"):
                get_current_user_id()


def test_get_current_user_id_inactive_user_raises(app):
    with app.app_context():
        inactive = User.query.filter(User.is_active.is_(False)).first()
        if inactive is None:
            pytest.skip("sin usuario inactivo en BD test")
        token = create_access_token(identity=str(inactive.id))
        with app.test_request_context(
            "/", headers={"Authorization": f"Bearer {token}"}
        ):
            verify_jwt_in_request()
            with pytest.raises(ValueError, match="Usuario no autorizado"):
                get_current_user_id()


def test_validate_actor_user_id_ok(app, actor_user_id):
    with app.app_context():
        assert validate_actor_user_id(actor_user_id) == actor_user_id


def test_validate_actor_user_id_inexistente(app):
    with app.app_context():
        with pytest.raises(ValueError):
            validate_actor_user_id(999999999)


def test_sync_sin_actor_falla():
    with pytest.raises(TypeError):
        sync_iniciadores_reinspeccion_notificacion()


def test_post_ruta_sin_jwt_401(client):
    resp = client.post("/rutas-trabajo", json={})
    assert resp.status_code == 401


def test_static_no_fallback_patterns_in_audit_services():
    """Guard: no debe quedar get_current_user_id_or_fallback ni fallback_user en servicios audit."""
    backend = Path(__file__).resolve().parents[1] / "app"
    forbidden = (
        "get_current_user_id_or_fallback",
        "fallback_user",
    )
    targets = [
        backend / "domains" / "rutas_trabajo" / "services" / "auth_service.py",
        backend / "domains" / "actuaciones" / "services" / "notificacion_iniciador_service.py",
        backend / "domains" / "relevamientos" / "services" / "relevamiento_iniciador_service.py",
        backend / "domains" / "actuaciones" / "services" / "oficio_iniciador_service.py",
    ]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} contiene {token}"


def test_no_order_by_id_first_fallback_in_auth_service():
    src = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "domains"
        / "rutas_trabajo"
        / "services"
        / "auth_service.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "first":
            raise AssertionError("auth_service no debe usar .first() como fallback de actor")
