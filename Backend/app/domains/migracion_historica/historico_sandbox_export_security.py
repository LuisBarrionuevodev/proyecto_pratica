"""
Guardas de seguridad para exports read-only desde ``digitaliza_sandbox`` local.

Reutiliza ``parse_database_identity`` del aislamiento de tests; criterio inverso:
solo sandbox local, nunca test ni hosts remotos.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from app.security.test_database import development_database_uri, parse_database_identity

ALLOWED_SANDBOX_DATABASE = "digitaliza_sandbox"
ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

FORBIDDEN_DATABASE_NAMES = frozenset(
    {
        "digitaliza_test",
        "digitaliza_pilot",
        "digitaliza",
        "produccion",
        "production",
        "mi_db",
    }
)

FORBIDDEN_HOST_SUBSTRINGS = (
    "railway",
    "rlwy.net",
    "amazonaws",
    "vercel",
    "staging",
    "prod.",
)


class HistoricoExportSecurityError(RuntimeError):
    """URI o entorno no permitido para export histórico."""


@dataclass(frozen=True)
class SanitizedDatabaseTarget:
    """Identidad de base para el resumen JSON (sin credenciales)."""

    driver: str
    host: str
    port: Optional[int]
    database: str


def resolve_export_database_uri(explicit_uri: Optional[str] = None) -> str:
    """
    Resuelve URI para export: explícita o ``SQLALCHEMY_DATABASE_URI`` de desarrollo.

    Raises:
        HistoricoExportSecurityError: URI ausente o inválida tras validación.
    """
    uri = (explicit_uri or development_database_uri() or os.getenv("DATABASE_URL") or "").strip()
    if not uri:
        raise HistoricoExportSecurityError(
            "No hay URI de base configurada. Defina SQLALCHEMY_DATABASE_URI en Backend/.env "
            "apuntando a digitaliza_sandbox en localhost."
        )
    validate_sandbox_export_database_uri(uri)
    return uri


def validate_sandbox_export_database_uri(uri: str) -> SanitizedDatabaseTarget:
    """
    Valida que la URI sea sandbox local read-only permitido.

    Args:
        uri: URI SQLAlchemy completa (no se registra en logs).

    Returns:
        Identidad sanitizada para resúmenes.

    Raises:
        HistoricoExportSecurityError: base, host o entorno no permitidos.
    """
    try:
        driver, host, port, database = parse_database_identity(uri)
    except Exception as exc:
        raise HistoricoExportSecurityError("URI de base de datos inválida.") from exc

    db = database.lower()
    h = host.lower()

    if db in FORBIDDEN_DATABASE_NAMES:
        raise HistoricoExportSecurityError(
            f"Base '{database}' no permitida para export histórico (use solo digitaliza_sandbox local)."
        )
    if db != ALLOWED_SANDBOX_DATABASE:
        raise HistoricoExportSecurityError(
            f"Export histórico limitado a '{ALLOWED_SANDBOX_DATABASE}' (recibido: '{database}')."
        )
    if h not in ALLOWED_HOSTS:
        raise HistoricoExportSecurityError(
            f"Host '{host}' no permitido; use localhost o 127.0.0.1."
        )
    for frag in FORBIDDEN_HOST_SUBSTRINGS:
        if frag in h or frag in uri.lower():
            raise HistoricoExportSecurityError("URI remota o de cloud no permitida para este export.")

    env = (os.getenv("ENVIRONMENT") or os.getenv("FLASK_ENV") or "development").strip().lower()
    if env in ("production", "prod", "staging"):
        raise HistoricoExportSecurityError("Export histórico bloqueado en entorno production/staging.")

    return SanitizedDatabaseTarget(driver=driver, host=h, port=port, database=db)
