import os
from uuid import uuid4

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
def service_actor(app):
    """
    Usuario activo de test para auditoría explícita (no fallback, no hardcode id=1).

    Retorna el id del usuario creado/activo para el test.
    """
    from app.database import db
    from app.models import User

    with app.app_context():
        suffix = uuid4().hex[:12]
        user = User(
            username=f"pytest_actor_{suffix}",
            email=f"pytest_actor_{suffix}@t.local",
            password_hash="x",
            role="usuario",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        yield int(user.id)
        db.session.rollback()


@pytest.fixture()
def actor_user_id(service_actor):
    """Alias: id del actor explícito del test."""
    return service_actor


@pytest.fixture()
def app_ctx(app, actor_user_id):
    """
    App context + JWT strict para tests que invocan services sin actor_user_id explícito.

    Opt-in por fixture (no autouse). Los tests negativos de auth deben evitar esta fixture.
    """
    from app.database import db
    from tests.helpers.service_actor import jwt_request_context

    with jwt_request_context(app, actor_user_id):
        yield app
        db.session.rollback()


@pytest.fixture()
def auth_headers(app, service_actor):
    """
    Authorization Bearer para rutas protegidas en fase 1 (mutaciones).
    Usa service_actor (usuario activo de test), no hardcode id=1.
    """
    with app.app_context():
        token = create_access_token(identity=str(service_actor))
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
