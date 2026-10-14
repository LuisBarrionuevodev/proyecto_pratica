"""
Conexión efectiva verificada para migración histórica (V1.1-MIG-ACTAS.1B).

Una URI explícita es la única fuente de verdad; se comprueba con ``SELECT DATABASE()``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional
from urllib.parse import unquote

from flask import Flask
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import create_app
from app.domains.migracion_historica.historico_migracion_import_security import (
    ALLOWED_MIGRACION_DATABASE,
    HistoricoMigracionImportSecurityError,
    MigracionImportTarget,
    validate_migracion_import_database_uri,
)


class MigracionTargetConnectionError(RuntimeError):
    """La conexión real no coincide con el destino declarado."""


@dataclass(frozen=True)
class VerifiedMigracionConnection:
    """Resultado de verificación contra ``SELECT DATABASE()``."""

    target: MigracionImportTarget
    database_efectiva: str
    conexion_verificada: bool = True


def database_name_from_uri(uri: str) -> str:
    """Extrae el nombre de base desde una URI SQLAlchemy (sin credenciales en logs)."""
    return unquote(uri.rsplit("/", 1)[-1].split("?", 1)[0])


def pin_explicit_database_uri(uri: str) -> str:
    """
    Fija la URI explícita como única fuente efectiva para la app.

    Elimina ``DATABASE_URL`` del entorno para que no prevalezca sobre la URI pasada.
    """
    cleaned = uri.strip()
    if not cleaned:
        raise ValueError("URI de base de datos vacía.")
    os.environ["SQLALCHEMY_DATABASE_URI"] = cleaned
    os.environ.pop("DATABASE_URL", None)
    return cleaned


def create_migracion_flask_app(
    database_uri: str,
    *,
    extra_config: Optional[Mapping[str, Any]] = None,
) -> Flask:
    """
    Crea la app Flask usando únicamente la URI explícita de migración histórica.

    Args:
        database_uri: debe pasar ``validate_migracion_import_database_uri``.
        extra_config: claves adicionales de configuración Flask.

    Returns:
        Instancia Flask con SQLAlchemy apuntando a la URI indicada.

    Raises:
        HistoricoMigracionImportSecurityError: destino no permitido.
    """
    uri = pin_explicit_database_uri(database_uri)
    validate_migracion_import_database_uri(uri)
    config: Dict[str, Any] = {
        "JWT_SECRET_KEY": "migracion-historica-jwt-secret-32ch",
        "SQLALCHEMY_DATABASE_URI": uri,
    }
    if extra_config:
        config.update(dict(extra_config))
    return create_app(config)


def fetch_effective_database_name(session: Session) -> Optional[str]:
    """Ejecuta ``SELECT DATABASE()`` en la sesión activa."""
    return session.execute(text("SELECT DATABASE()")).scalar()


def verify_effective_database_name(
    session: Session,
    expected_database: str,
) -> str:
    """
    Comprueba que la base conectada coincide con la esperada.

    Args:
        session: sesión SQLAlchemy con conexión abierta.
        expected_database: nombre de base declarado en la URI.

    Returns:
        Nombre efectivo de la base (minúsculas).

    Raises:
        MigracionTargetConnectionError: si no hay coincidencia o la base está vacía.
    """
    expected = (expected_database or "").strip().lower()
    if not expected:
        raise MigracionTargetConnectionError("Nombre de base destino vacío o inválido.")
    actual_raw = fetch_effective_database_name(session)
    actual = (actual_raw or "").strip().lower()
    if not actual:
        raise MigracionTargetConnectionError(
            "No hay base seleccionada en la conexión (SELECT DATABASE() vacío)."
        )
    if actual != expected:
        raise MigracionTargetConnectionError(
            f"Conexión efectiva '{actual}' no coincide con destino esperado '{expected}'."
        )
    return actual


def verify_pilot_target_connection(
    session: Session,
    target: MigracionImportTarget,
) -> VerifiedMigracionConnection:
    """
    Verifica que ``SELECT DATABASE()`` coincide con el destino declarado del piloto.

    Args:
        session: sesión activa (requiere app context).
        target: destino (p. ej. ``digitaliza_migracion`` en CLI o ``digitaliza_test`` en pytest).

    Returns:
        VerifiedMigracionConnection para resúmenes seguros.

    Raises:
        MigracionTargetConnectionError: desajuste entre URI y conexión real.
    """
    efectiva = verify_effective_database_name(session, target.database)
    return VerifiedMigracionConnection(
        target=target,
        database_efectiva=efectiva,
        conexion_verificada=True,
    )


def verify_migracion_connection(
    session: Session,
    target: MigracionImportTarget,
) -> VerifiedMigracionConnection:
    """
    Verifica que la sesión está en ``digitaliza_migracion`` local declarado.

    Args:
        session: sesión activa (requiere app context).
        target: destino ya validado por URI.

    Returns:
        VerifiedMigracionConnection para resúmenes seguros.

    Raises:
        MigracionTargetConnectionError: desajuste entre URI y conexión real.
    """
    if target.database.lower() != ALLOWED_MIGRACION_DATABASE:
        raise HistoricoMigracionImportSecurityError(
            f"Verificación de conexión limitada a '{ALLOWED_MIGRACION_DATABASE}'."
        )
    return verify_pilot_target_connection(session, target)


def connection_summary_fields(verified: VerifiedMigracionConnection) -> Dict[str, Any]:
    """Campos JSON seguros para resúmenes de migración."""
    return {
        "database_destino_efectiva": verified.database_efectiva,
        "host_destino_efectivo": verified.target.host,
        "conexion_verificada": verified.conexion_verificada,
    }


def verify_explicit_uri_connection(session: Session, database_uri: str) -> str:
    """
    Verifica conexión para cualquier ``--database-uri`` explícito (p. ej. seed).

    Args:
        session: sesión activa.
        database_uri: URI usada para configurar la app.

    Returns:
        Nombre de base efectivo verificado.

    Raises:
        MigracionTargetConnectionError: URI y conexión no coinciden.
    """
    expected = database_name_from_uri(database_uri)
    return verify_effective_database_name(session, expected)
