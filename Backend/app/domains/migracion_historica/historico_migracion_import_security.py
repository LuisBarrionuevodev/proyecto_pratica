"""
Guardas de seguridad para importación histórica en ``digitaliza_migracion`` local.

V1.1-MIG-ACTAS.1A — nunca sandbox, test, Railway ni producción.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from app.security.test_database import parse_database_identity

ALLOWED_MIGRACION_DATABASE = "digitaliza_migracion"
ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

FORBIDDEN_DATABASE_NAMES = frozenset(
    {
        "digitaliza_sandbox",
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


class HistoricoMigracionImportSecurityError(RuntimeError):
    """URI o entorno no permitido para importación histórica."""


@dataclass(frozen=True)
class MigracionImportTarget:
    """Identidad sanitizada del destino (sin credenciales)."""

    driver: str
    host: str
    port: Optional[int]
    database: str


def validate_migracion_import_database_uri(uri: str) -> MigracionImportTarget:
    """
    Valida que la URI apunte solo a ``digitaliza_migracion`` en localhost.

    Args:
        uri: URI SQLAlchemy completa (no loguear).

    Returns:
        MigracionImportTarget para resúmenes.

    Raises:
        HistoricoMigracionImportSecurityError: base u host no permitidos.
    """
    try:
        driver, host, port, database = parse_database_identity(uri)
    except Exception as exc:
        raise HistoricoMigracionImportSecurityError("URI de base de datos inválida.") from exc

    db = database.lower()
    h = host.lower()

    if db in FORBIDDEN_DATABASE_NAMES:
        raise HistoricoMigracionImportSecurityError(
            f"Base '{database}' prohibida para importación histórica."
        )
    if db != ALLOWED_MIGRACION_DATABASE:
        raise HistoricoMigracionImportSecurityError(
            f"Importación histórica limitada a '{ALLOWED_MIGRACION_DATABASE}' "
            f"(recibido: '{database}')."
        )
    if h not in ALLOWED_HOSTS:
        raise HistoricoMigracionImportSecurityError(
            f"Host '{host}' no permitido; use localhost o 127.0.0.1."
        )
    for frag in FORBIDDEN_HOST_SUBSTRINGS:
        if frag in h or frag in uri.lower():
            raise HistoricoMigracionImportSecurityError(
                "URI remota o de cloud no permitida para importación histórica."
            )

    env = (os.getenv("ENVIRONMENT") or os.getenv("FLASK_ENV") or "development").strip().lower()
    if env in ("production", "prod", "staging"):
        raise HistoricoMigracionImportSecurityError(
            "Importación histórica bloqueada en entorno production/staging."
        )

    return MigracionImportTarget(driver=driver, host=h, port=port, database=db)
