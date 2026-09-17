import os

import pytest
from flask_jwt_extended import create_access_token

from app import create_app


@pytest.fixture()
def app():
    os.environ["GEO_POST_COMMIT_ASYNC"] = "false"
    flask_app = create_app(
        {
            "TESTING": True,
            "PROPAGATE_EXCEPTIONS": True,  # ✅ clave: que la excepción suba y pytest muestre traceback
            "JWT_SECRET_KEY": "pytest-jwt-secret-key-32bytes-min",
            "RATELIMIT_ENABLED": False,
        }
    )
    yield flask_app
    from app.domains.geolocalizacion.geocode.services import geocode_post_commit_worker as worker_mod

    worker_mod.shutdown_geocode_post_commit_worker()
    worker_mod._executor = None
    worker_mod._app = None
    worker_mod._drain_scheduled = False


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
