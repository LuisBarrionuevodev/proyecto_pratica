import pytest
from app import create_app

@pytest.fixture()
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        PROPAGATE_EXCEPTIONS=True,  # ✅ clave: que la excepción suba y pytest muestre traceback
    )
    return app

@pytest.fixture()
def client(app):
    return app.test_client()
