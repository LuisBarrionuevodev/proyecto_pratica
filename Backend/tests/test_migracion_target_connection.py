"""Tests V1.1-MIG-ACTAS.1B — conexión efectiva verificada para migración histórica."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from app.domains.migracion_historica.historico_migracion_import_security import (
    HistoricoMigracionImportSecurityError,
    MigracionImportTarget,
    validate_migracion_import_database_uri,
)
from app.domains.migracion_historica.migracion_target_connection import (
    MigracionTargetConnectionError,
    connection_summary_fields,
    create_migracion_flask_app,
    pin_explicit_database_uri,
    verify_effective_database_name,
    verify_explicit_uri_connection,
    verify_migracion_connection,
    verify_pilot_target_connection,
)

MIGRACION_URI = "mysql+pymysql://root:super_secret_pw@127.0.0.1:3306/digitaliza_migracion"
SANDBOX_URI = "mysql+pymysql://root:super_secret_pw@127.0.0.1:3306/digitaliza_sandbox"


def _session_returning_database(name: str | None) -> MagicMock:
    session = MagicMock()
    session.execute.return_value.scalar.return_value = name
    return session


def test_validate_rechaza_sandbox_uri() -> None:
    with pytest.raises(HistoricoMigracionImportSecurityError, match="sandbox"):
        validate_migracion_import_database_uri(SANDBOX_URI)


def test_pin_explicit_uri_elimina_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", SANDBOX_URI)
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", SANDBOX_URI)
    uri = pin_explicit_database_uri(MIGRACION_URI)
    assert uri == MIGRACION_URI
    assert os.environ["SQLALCHEMY_DATABASE_URI"] == MIGRACION_URI
    assert "DATABASE_URL" not in os.environ


def test_verify_effective_database_mismatch() -> None:
    session = _session_returning_database("digitaliza_sandbox")
    with pytest.raises(MigracionTargetConnectionError, match="digitaliza_sandbox"):
        verify_effective_database_name(session, "digitaliza_migracion")


def test_verify_explicit_uri_connection_ok() -> None:
    session = _session_returning_database("digitaliza_migracion")
    assert verify_explicit_uri_connection(session, MIGRACION_URI) == "digitaliza_migracion"


def test_connection_summary_sin_secretos() -> None:
    target = validate_migracion_import_database_uri(MIGRACION_URI)
    session = _session_returning_database("digitaliza_migracion")
    verified = verify_migracion_connection(session, target)
    fields = connection_summary_fields(verified)
    blob = str(fields)
    assert "super_secret" not in blob
    assert "mysql+pymysql" not in blob
    assert fields == {
        "database_destino_efectiva": "digitaliza_migracion",
        "host_destino_efectivo": "127.0.0.1",
        "conexion_verificada": True,
    }


def test_verify_pilot_target_acepta_test_db() -> None:
    target = MigracionImportTarget(
        driver="mysql+pymysql",
        host="localhost",
        port=3306,
        database="digitaliza_test",
    )
    session = _session_returning_database("digitaliza_test")
    verified = verify_pilot_target_connection(session, target)
    assert verified.database_efectiva == "digitaliza_test"


def test_create_migracion_flask_app_configura_uri_explicita(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", SANDBOX_URI)
    app = create_migracion_flask_app(MIGRACION_URI)
    assert app.config["SQLALCHEMY_DATABASE_URI"] == MIGRACION_URI
    assert "digitaliza_sandbox" not in app.config["SQLALCHEMY_DATABASE_URI"]
