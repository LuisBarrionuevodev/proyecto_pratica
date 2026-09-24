"""
Guardas de base de datos en entornos productivos (piloto / production).

Qué hace: impide arrancar la app cloud contra bases de desarrollo, test o sandbox.
Parámetros: URI SQLAlchemy resuelta.
Errores: RuntimeError si el nombre de base está prohibido.
"""

from __future__ import annotations

from sqlalchemy.engine import make_url

from app.security.test_database import parse_database_identity

# Nombre canónico acordado para el piloto cloud (Railway MySQL).
PILOT_DATABASE_NAME = "digitaliza_pilot"

# Bases que nunca deben usarse como destino productivo.
FORBIDDEN_PRODUCTION_DATABASE_NAMES = frozenset(
    {
        "digitaliza_test",
        "digitaliza_sandbox",
        "digitaliza",
        "mi_db",
        "produccion",
        "production",
    }
)


def database_name_from_uri(uri: str) -> str:
    """Extrae el nombre de schema de una URI SQLAlchemy."""
    return parse_database_identity(uri)[3]


def assert_production_database_allowed(uri: str) -> None:
    """
    Falla al arrancar si la URI apunta a una base prohibida en producción.

    Parámetros:
        uri: ``SQLALCHEMY_DATABASE_URI`` efectiva.

    Errores:
        RuntimeError: base prohibida o URI inválida.
    """
    if not uri or not str(uri).strip():
        raise RuntimeError("SQLALCHEMY_DATABASE_URI es obligatoria en staging/production.")

    try:
        name = database_name_from_uri(uri)
    except Exception as exc:
        raise RuntimeError(f"URI de base de datos inválida en producción: {uri}") from exc

    if name in FORBIDDEN_PRODUCTION_DATABASE_NAMES:
        raise RuntimeError(
            f"La base '{name}' está prohibida en staging/production. "
            f"Use una instancia dedicada (ej. {PILOT_DATABASE_NAME})."
        )
