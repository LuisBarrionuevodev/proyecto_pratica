import os

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.security.test_database import (
    assert_connected_database_is_test,
    assert_test_database_migrated_to_head,
    bootstrap_pytest_database_environment,
)


def pytest_configure(config):
    """Fija TEST_DATABASE_URL como URI efectiva para todo el proceso pytest."""
    bootstrap_pytest_database_environment()


@pytest.fixture()
def app():
    os.environ["GEO_POST_COMMIT_ASYNC"] = "false"
    flask_app = create_app(
        {
            "TESTING": True,
            "PROPAGATE_EXCEPTIONS": True,
            "JWT_SECRET_KEY": "pytest-jwt-secret-key-32bytes-min",
            "RATELIMIT_ENABLED": False,
        }
    )
    assert_test_database_migrated_to_head(flask_app)
    assert_connected_database_is_test(flask_app)
    yield flask_app
    from app.domains.geolocalizacion.geocode.services import geocode_post_commit_worker as worker_mod

    worker_mod.shutdown_geocode_post_commit_worker()
    worker_mod._executor = None
    worker_mod._app = None
    worker_mod._drain_scheduled = False
    worker_mod._drain_rerun_needed = False


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
