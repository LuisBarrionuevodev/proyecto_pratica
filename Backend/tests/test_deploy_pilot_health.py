"""DEPLOY-PILOT.1 — healthcheck y guardas de producción."""

from __future__ import annotations

import pytest

from app import create_app
from app.security.production_database import assert_production_database_allowed


def test_health_endpoint_returns_200(app_ctx) -> None:
    client = app_ctx.test_client()
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}


def test_production_db_guard_rejects_sandbox() -> None:
    with pytest.raises(RuntimeError, match="digitaliza_sandbox"):
        assert_production_database_allowed(
            "mysql+pymysql://u:p@localhost:3306/digitaliza_sandbox"
        )


def test_production_db_guard_rejects_test() -> None:
    with pytest.raises(RuntimeError, match="digitaliza_test"):
        assert_production_database_allowed(
            "mysql+pymysql://u:p@localhost:3306/digitaliza_test"
        )


def test_production_db_guard_allows_pilot() -> None:
    assert_production_database_allowed(
        "mysql+pymysql://u:p@localhost:3306/digitaliza_pilot"
    ) is None


def test_strict_config_sets_debug_false(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 40)
    monkeypatch.setenv(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://u:p@localhost:3306/digitaliza_pilot",
    )
    monkeypatch.setenv("CORS_ORIGINS", "https://example.vercel.app")
    app = create_app()
    assert app.config["DEBUG"] is False
    assert app.config["TESTING"] is False


def test_json_404_handler(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    app = create_app()
    client = app.test_client()
    res = client.get("/ruta-inexistente-deploy-pilot")
    assert res.status_code == 404
    assert res.is_json
    assert res.get_json()["detail"] == "Not found"
