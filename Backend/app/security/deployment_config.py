"""
Validación de configuración según entorno de despliegue.

Qué hace: en staging/production exige secretos y DB no por defecto; parsea CORS.
Parámetros: app Flask tras cargar config.
Errores: RuntimeError al arrancar si la configuración es insegura.
"""

from __future__ import annotations

import os
from typing import Any

from flask import Flask

# Deben coincidir con los defaults en app.main.create_app (detección de "olvidé configurar prod").
DEFAULT_INSECURE_JWT_SECRET = "dev-change-this-secret"
DEFAULT_INSECURE_SQLALCHEMY_URI = "mysql+pymysql://root:1234@localhost/mi_db"

_MIN_JWT_SECRET_LEN = 32


def deployment_is_strict() -> bool:
    """
    Entornos donde no se permiten defaults inseguros.

    Usa `ENVIRONMENT` (preferido) o `FLASK_ENV` en minúsculas:
    production | prod | staging
    """
    raw = (os.getenv("ENVIRONMENT") or os.getenv("FLASK_ENV") or "development").strip().lower()
    return raw in ("production", "prod", "staging")


def parse_cors_origins(*, strict: bool) -> list[str]:
    """
    Orígenes CORS desde `CORS_ORIGINS` (coma-separado).

    En desarrollo, si está vacío usa solo `http://localhost:5173`.
    En strict, lista vacía → RuntimeError.
    """
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        if strict:
            raise RuntimeError(
                "CORS_ORIGINS es obligatorio en staging/production "
                "(ej. CORS_ORIGINS=http://localhost:5173,https://app.ejemplo.gob.ar)."
            )
        return ["http://localhost:5173"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def enforce_strict_runtime_config(app: Flask) -> None:
    """
    Falla al arrancar en staging/production si JWT o DB siguen en valores de desarrollo.

    Omite si `TESTING=True` (pytest) o `SKIP_STRICT_CONFIG=1` (solo emergencias en CI).
    """
    if app.config.get("TESTING"):
        return
    if os.getenv("SKIP_STRICT_CONFIG", "").strip() == "1":
        return
    if not deployment_is_strict():
        return

    jwt_secret = app.config.get("JWT_SECRET_KEY")
    if not jwt_secret or not isinstance(jwt_secret, str):
        raise RuntimeError("JWT_SECRET_KEY es obligatorio en staging/production.")
    if jwt_secret == DEFAULT_INSECURE_JWT_SECRET or len(jwt_secret.strip()) < _MIN_JWT_SECRET_LEN:
        raise RuntimeError(
            f"JWT_SECRET_KEY debe ser distinto del default de desarrollo y tener al menos "
            f"{_MIN_JWT_SECRET_LEN} caracteres en staging/production."
        )

    uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    if not uri or not isinstance(uri, str):
        raise RuntimeError("SQLALCHEMY_DATABASE_URI es obligatorio en staging/production.")
    if uri.strip() == DEFAULT_INSECURE_SQLALCHEMY_URI:
        raise RuntimeError(
            "SQLALCHEMY_DATABASE_URI no puede ser el default inseguro de desarrollo "
            "en staging/production."
        )


def apply_cors(app: Flask, cors_origins: list[str]) -> Any:
    """Registra Flask-CORS con orígenes explícitos."""
    from flask_cors import CORS

    return CORS(
        app,
        resources={r"/*": {"origins": cors_origins}},
        supports_credentials=False,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
