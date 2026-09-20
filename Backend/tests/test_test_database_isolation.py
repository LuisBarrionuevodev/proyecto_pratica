"""
PREDEPLOY-CLEANUP.1 — guardas de aislamiento TEST_DATABASE_URL vs Development.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from flask import Flask

from app import create_app
from app.security.test_database import (
    MISSING_TEST_URL_MESSAGE,
    PRODUCTION_STAGING_MESSAGE,
    SAME_AS_DEV_MESSAGE,
    DatabaseTestConfigError,
    assert_pytest_allowed_in_current_deployment,
    assert_test_database_name_allowed,
    bootstrap_pytest_database_environment,
    configure_app_for_testing,
    database_name_from_uri,
    require_test_database_url,
    validate_test_database_url,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEV_URI = "mysql+pymysql://root:pass@localhost:3306/digitaliza_sandbox"
TEST_URI = "mysql+pymysql://root:pass@localhost:3306/digitaliza_test"


def test_a_require_test_database_url_absent(monkeypatch):
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    with pytest.raises(DatabaseTestConfigError) as exc:
        require_test_database_url()
    assert "TEST_DATABASE_URL es obligatoria" in str(exc.value)


def test_b_test_url_equals_dev_aborts():
    with pytest.raises(DatabaseTestConfigError) as exc:
        validate_test_database_url(TEST_URI, dev_uri=TEST_URI)
    assert SAME_AS_DEV_MESSAGE.split("\n")[0] in str(exc.value)


def test_c_database_without_test_in_name_aborts():
    with pytest.raises(DatabaseTestConfigError) as exc:
        assert_test_database_name_allowed("digitaliza_sandbox")
    assert "debe contener 'test'" in str(exc.value)


def test_d_valid_test_vs_dev_allowed():
    uri = validate_test_database_url(TEST_URI, dev_uri=DEV_URI)
    assert uri == TEST_URI


def test_e_create_app_testing_uses_test_database_uri(app):
    """TESTING=True: configure_app_for_testing fija digitaliza_test."""
    assert database_name_from_uri(app.config["SQLALCHEMY_DATABASE_URI"]) == "digitaliza_test"


def test_f_create_app_without_testing_override_uses_env_test_uri():
    """Tests legacy con create_app() sin TESTING usan SQLALCHEMY_DATABASE_URI del bootstrap."""
    assert database_name_from_uri(os.environ["SQLALCHEMY_DATABASE_URI"]) == "digitaliza_test"
    legacy_app = create_app()
    assert database_name_from_uri(legacy_app.config["SQLALCHEMY_DATABASE_URI"]) == "digitaliza_test"


def test_g_production_environment_aborts(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(DatabaseTestConfigError) as exc:
        assert_pytest_allowed_in_current_deployment()
    assert PRODUCTION_STAGING_MESSAGE in str(exc.value)


def test_h_staging_environment_aborts(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "staging")
    with pytest.raises(DatabaseTestConfigError) as exc:
        assert_pytest_allowed_in_current_deployment()
    assert PRODUCTION_STAGING_MESSAGE in str(exc.value)


def test_protected_sandbox_name_rejected():
    with pytest.raises(DatabaseTestConfigError):
        assert_test_database_name_allowed("digitaliza_sandbox")


def test_configure_app_for_testing_rejects_dev_uri(monkeypatch):
    monkeypatch.setenv("PYTEST_ORIGINAL_DEV_DATABASE_URI", DEV_URI)
    app = Flask(__name__)
    app.config["TESTING"] = True
    with pytest.raises(DatabaseTestConfigError):
        configure_app_for_testing(
            app,
            config_override={"SQLALCHEMY_DATABASE_URI": DEV_URI},
        )


def test_no_fallback_message_content():
    assert "No se permite fallback" in MISSING_TEST_URL_MESSAGE


def test_pytest_subprocess_aborts_when_test_url_missing():
    """Arranque de pytest sin TEST_DATABASE_URL debe fallar en pytest_configure."""
    env = os.environ.copy()
    env.pop("TEST_DATABASE_URL", None)
    env["SQLALCHEMY_DATABASE_URI"] = DEV_URI
    env.pop("PYTEST_ORIGINAL_DEV_DATABASE_URI", None)
    env["PYTEST_SKIP_DOTENV"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_iniciador_estado_normalization.py", "-q"],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "TEST_DATABASE_URL es obligatoria" in combined


def test_connected_database_is_test(app):
    """Prueba de no contaminación real (requiere digitaliza_test migrada)."""
    from sqlalchemy import text

    from app.database import db

    test_db = database_name_from_uri(os.environ["TEST_DATABASE_URL"])
    dev_db = database_name_from_uri(os.environ.get("PYTEST_ORIGINAL_DEV_DATABASE_URI", DEV_URI))
    with app.app_context():
        current = db.session.execute(text("SELECT DATABASE()")).scalar()
    assert (current or "").lower() == test_db
    assert (current or "").lower() != dev_db
