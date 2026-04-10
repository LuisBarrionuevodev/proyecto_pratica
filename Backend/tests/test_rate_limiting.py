"""Rate limiting en endpoints críticos (Flask-Limiter)."""

import pytest

from app import create_app


@pytest.fixture()
def app_rate_limited(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_LOGIN", "2 per second")
    return create_app(
        {
            "TESTING": True,
            "JWT_SECRET_KEY": "pytest-jwt-secret-key-32bytes-min",
            "RATELIMIT_ENABLED": True,
            "RATELIMIT_STORAGE_URI": "memory://",
        }
    )


@pytest.fixture()
def client_rl(app_rate_limited):
    return app_rate_limited.test_client()


def test_login_excede_limite_devuelve_429(client_rl):
    """Tras 2 POST válidos en la ventana, el siguiente recibe 429."""
    for _ in range(2):
        r = client_rl.post("/api/auth/login", json={"username": "u", "password": "p"})
        assert r.status_code != 429, r.get_data(as_text=True)

    r429 = client_rl.post("/api/auth/login", json={"username": "u", "password": "p"})
    assert r429.status_code == 429
    body = r429.get_json()
    assert body is not None
    assert "detail" in body


def test_rate_limiting_desactivado_en_suite_principal(client):
    """Fixture estándar (RATELIMIT_ENABLED=False): login no debe devolver 429 por límite."""
    for _ in range(8):
        r = client.post("/api/auth/login", json={"username": "u", "password": "p"})
        assert r.status_code != 429
