import pytest
from flask_jwt_extended import create_access_token

from app import create_app


@pytest.fixture()
def app():
    return create_app(
        {
            "TESTING": True,
            "PROPAGATE_EXCEPTIONS": True,  # ✅ clave: que la excepción suba y pytest muestre traceback
            "JWT_SECRET_KEY": "pytest-jwt-secret-key-32bytes-min",
            "RATELIMIT_ENABLED": False,
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_headers(app):
    """
    Authorization Bearer para rutas protegidas en fase 1 (mutaciones).
    No valida existencia de usuario en BD; solo firma JWT válida.
    """
    with app.app_context():
        token = create_access_token(identity="1")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
