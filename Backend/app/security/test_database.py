"""
Guardas de aislamiento: pytest / TESTING nunca deben usar la DB de Development.

Qué hace: valida TEST_DATABASE_URL, compara con Development y configura la URI de tests.
Errores: DatabaseTestConfigError / DatabaseTestSchemaError con mensajes accionables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[2]

PROTECTED_NON_TEST_DATABASE_NAMES = frozenset(
    {
        "digitaliza_sandbox",
        "digitaliza",
        "produccion",
        "production",
    }
)

TEST_DATABASE_URL_ENV = "TEST_DATABASE_URL"
PYTEST_ORIGINAL_DEV_DATABASE_URI_ENV = "PYTEST_ORIGINAL_DEV_DATABASE_URI"

MIGRATION_REQUIRED_MESSAGE = (
    "La base digitaliza_test no está migrada a Alembic HEAD.\n"
    "Ejecute las migraciones antes de correr pytest:\n"
    "  cd Backend\n"
    "  python scripts/migrate_test_db.py\n"
    "o bien:\n"
    "  set SQLALCHEMY_DATABASE_URI=%(test_url)s  (PowerShell: $env:SQLALCHEMY_DATABASE_URI=...)\n"
    "  flask db upgrade"
)

MISSING_TEST_URL_MESSAGE = (
    "TEST_DATABASE_URL es obligatoria para ejecutar tests backend con DB.\n"
    "No se permite fallback a la base de desarrollo.\n\n"
    "Pasos:\n"
    "  1. Crear la base vacía: digitaliza_test\n"
    "  2. En Backend/.env definir TEST_DATABASE_URL=mysql+pymysql://USER:PASS@localhost:3306/digitaliza_test\n"
    "  3. Aplicar migraciones: python scripts/migrate_test_db.py\n"
    "  4. Volver a ejecutar: pytest"
)

SAME_AS_DEV_MESSAGE = (
    "La base de tests no puede ser la misma que la base Development.\n"
    "Use una base dedicada (ej. digitaliza_test) distinta de digitaliza_sandbox."
)

PRODUCTION_STAGING_MESSAGE = (
    "No se permiten tests backend con acceso a DB en entornos production/staging."
)


class DatabaseTestConfigError(RuntimeError):
    """Configuración de base de tests inválida o insegura."""


class DatabaseTestSchemaError(RuntimeError):
    """Esquema de la base de tests incompleto (falta migración Alembic)."""


def deployment_environment_name() -> str:
    """Nombre de entorno efectivo (ENVIRONMENT o FLASK_ENV)."""
    return (os.getenv("ENVIRONMENT") or os.getenv("FLASK_ENV") or "development").strip().lower()


def assert_pytest_allowed_in_current_deployment() -> None:
    """
    Bloquea pytest con DB en production/staging.

    TESTING=True no debe desactivar esta protección.
    """
    env = deployment_environment_name()
    if env in ("production", "prod", "staging"):
        raise DatabaseTestConfigError(PRODUCTION_STAGING_MESSAGE)


def parse_database_identity(uri: str) -> tuple[str, str, int | None, str]:
    """
    Identidad lógica de una URI SQLAlchemy (driver, host, port, database).

    Ignora credenciales.
    """
    if not uri or not str(uri).strip():
        raise DatabaseTestConfigError("URI de base de datos vacía.")
    try:
        url = make_url(uri)
    except Exception as exc:  # pragma: no cover - mensaje genérico
        raise DatabaseTestConfigError(f"URI de base de datos inválida: {uri}") from exc

    driver = (url.drivername or "").lower()
    host = (url.host or "localhost").lower()
    port = url.port
    database = (url.database or "").lower()
    if not database:
        raise DatabaseTestConfigError(f"La URI no especifica nombre de base de datos: {uri}")
    return driver, host, port, database


def database_name_from_uri(uri: str) -> str:
    """Nombre de la base (schema) en la URI."""
    return parse_database_identity(uri)[3]


def assert_test_database_name_allowed(database_name: str) -> None:
    """Defensa secundaria: el nombre debe contener 'test'."""
    name = (database_name or "").lower()
    if "test" not in name:
        raise DatabaseTestConfigError(
            f"La base de tests debe contener 'test' en el nombre (recibido: '{database_name}'). "
            "Ejemplo válido: digitaliza_test."
        )
    if name in PROTECTED_NON_TEST_DATABASE_NAMES:
        raise DatabaseTestConfigError(
            f"La base '{database_name}' está protegida y no puede usarse como DB de pytest."
        )


def require_test_database_url() -> str:
    """Obtiene TEST_DATABASE_URL o aborta con instrucciones."""
    test_url = (os.getenv(TEST_DATABASE_URL_ENV) or "").strip()
    if not test_url:
        raise DatabaseTestConfigError(MISSING_TEST_URL_MESSAGE)
    return test_url


def development_database_uri() -> str:
    """URI de Development (guardada al bootstrap o leída del entorno)."""
    stored = (os.getenv(PYTEST_ORIGINAL_DEV_DATABASE_URI_ENV) or "").strip()
    if stored:
        return stored
    return (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()


def validate_test_database_url(
    test_url: str,
    *,
    dev_uri: str | None = None,
    check_deployment: bool = True,
) -> str:
    """
    Valida TEST_DATABASE_URL frente a Development y reglas de nombre.

    Retorna la URI de test validada.
    """
    if check_deployment:
        assert_pytest_allowed_in_current_deployment()

    test_url = (test_url or "").strip()
    if not test_url:
        raise DatabaseTestConfigError(MISSING_TEST_URL_MESSAGE)

    dev = (dev_uri if dev_uri is not None else development_database_uri()).strip()
    test_identity = parse_database_identity(test_url)
    assert_test_database_name_allowed(test_identity[3])

    if dev:
        dev_identity = parse_database_identity(dev)
        if test_identity == dev_identity:
            raise DatabaseTestConfigError(SAME_AS_DEV_MESSAGE)

    return test_url


def bootstrap_pytest_database_environment() -> str:
    """
    Ejecutar al inicio de pytest: guardas + fijar SQLALCHEMY_DATABASE_URI a la DB de tests.

    Guarda la URI Development original en PYTEST_ORIGINAL_DEV_DATABASE_URI.
    """
    if os.getenv("PYTEST_SKIP_DOTENV", "").strip() != "1":
        load_dotenv(BACKEND_ROOT / ".env", override=False)
    assert_pytest_allowed_in_current_deployment()
    test_url = require_test_database_url()
    dev_uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if dev_uri:
        os.environ.setdefault(PYTEST_ORIGINAL_DEV_DATABASE_URI_ENV, dev_uri)
    validate_test_database_url(test_url, dev_uri=dev_uri or development_database_uri())
    os.environ["SQLALCHEMY_DATABASE_URI"] = test_url
    return test_url


def configure_app_for_testing(app: Any, *, config_override: dict | None = None) -> None:
    """
    Fuerza la URI de tests en una app Flask con TESTING=True.

    Si config_override trae SQLALCHEMY_DATABASE_URI, también se valida.
    """
    assert_pytest_allowed_in_current_deployment()
    override = config_override or {}
    explicit_uri = override.get("SQLALCHEMY_DATABASE_URI")
    test_url = (explicit_uri or require_test_database_url()).strip()
    dev_uri = development_database_uri()
    validate_test_database_url(test_url, dev_uri=dev_uri)
    app.config["SQLALCHEMY_DATABASE_URI"] = test_url


def assert_test_database_migrated_to_head(app: Any) -> None:
    """
    Verifica que la DB de tests tenga Alembic al HEAD y columnas mínimas esperadas.

    No modifica el esquema (sin ALTER TABLE desde pytest).
    """
    from sqlalchemy import inspect, text

    from app.database import db

    with app.app_context():
        engine = db.engine
        insp = inspect(engine)
        if not insp.has_table("alembic_version"):
            raise DatabaseTestSchemaError(MIGRATION_REQUIRED_MESSAGE)

        with engine.connect() as conn:
            current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()

        if not current:
            raise DatabaseTestSchemaError(MIGRATION_REQUIRED_MESSAGE)

        from alembic.config import Config
        from alembic.script import ScriptDirectory

        migrations_dir = BACKEND_ROOT / "migrations"
        cfg = Config()
        cfg.set_main_option("script_location", str(migrations_dir))
        script = ScriptDirectory.from_config(cfg)
        heads = set(script.get_heads())
        if current not in heads:
            raise DatabaseTestSchemaError(
                f"{MIGRATION_REQUIRED_MESSAGE}\n"
                f"Revisión actual: {current}; HEAD esperado: {', '.join(sorted(heads)) or '(sin head)'}."
            )

        if insp.has_table("domicilio_geocode"):
            cols = {c["name"] for c in insp.get_columns("domicilio_geocode")}
            if "provider_place_id" not in cols:
                raise DatabaseTestSchemaError(MIGRATION_REQUIRED_MESSAGE)


def assert_connected_database_is_test(app: Any) -> None:
    """Prueba de no contaminación: la conexión activa debe ser TEST_DATABASE_URL."""
    from sqlalchemy import text

    from app.database import db

    test_url = require_test_database_url()
    test_db = database_name_from_uri(test_url)
    dev_db = database_name_from_uri(development_database_uri()) if development_database_uri() else None

    with app.app_context():
        with db.engine.connect() as conn:
            current = conn.execute(text("SELECT DATABASE()")).scalar()
        current_norm = (current or "").lower()
        if current_norm != test_db:
            raise DatabaseTestConfigError(
                f"La conexión activa usa '{current}', se esperaba la base de tests '{test_db}'."
            )
        if dev_db and current_norm == dev_db:
            raise DatabaseTestConfigError(
                "Contaminación detectada: pytest está conectado a la base Development."
            )
