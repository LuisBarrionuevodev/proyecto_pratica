"""
Rate limiting (Flask-Limiter) en endpoints críticos.

Storage: `RATE_LIMIT_STORAGE_URI` (default `memory://`). En multi-worker usar Redis, ej.
`redis://localhost:6379/0`.

Config Flask: `RATELIMIT_ENABLED` (False en tests). Límites por variable de entorno opcional.
"""

from __future__ import annotations

import os

from flask import Flask, jsonify, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def _env_limit(var: str, default: str) -> str:
    v = (os.getenv(var) or "").strip()
    return v if v else default


def _on_breach(request_limit):
    """Respuesta JSON alineada al resto de la API (status 429)."""
    _ = request_limit
    return make_response(
        jsonify({"detail": "Demasiadas solicitudes. Probá más tarde."}),
        429,
    )


# Límites leídos en cada chequeo (permite tests con monkeypatch de env).
def limit_login() -> str:
    return _env_limit("RATE_LIMIT_LOGIN", "5 per minute")


def limit_password_reset_request() -> str:
    return _env_limit("RATE_LIMIT_PASSWORD_RESET_REQUEST", "3 per hour")


def limit_password_reset_confirm() -> str:
    return _env_limit("RATE_LIMIT_PASSWORD_RESET_CONFIRM", "10 per 15 minutes")


def limit_epicollect_import() -> str:
    return _env_limit("RATE_LIMIT_EPICOLLECT_IMPORT", "30 per hour")


def limit_grid_commit_batch() -> str:
    return _env_limit("RATE_LIMIT_GRID_COMMIT_BATCH", "30 per minute")


def limit_grid_commit_row() -> str:
    return _env_limit("RATE_LIMIT_GRID_COMMIT_ROW", "60 per minute")


def limit_completar_trabajo_cerrar() -> str:
    return _env_limit("RATE_LIMIT_COMPLETAR_TRABAJO_CERRAR", "60 per hour")

limiter = Limiter(
    key_func=get_remote_address,
    on_breach=_on_breach,
    headers_enabled=True,
    swallow_errors=True,
)


def init_rate_limiter(app: Flask) -> Limiter:
    """
    Asocia el limiter global a la app y aplica storage desde env/config.

    Parámetros:
        app: aplicación Flask.

    Retorno:
        Instancia `Limiter` (singleton de módulo).
    """
    app.config.setdefault(
        "RATELIMIT_STORAGE_URI",
        os.getenv("RATE_LIMIT_STORAGE_URI", "memory://"),
    )
    app.config.setdefault("RATELIMIT_ENABLED", True)

    limiter.init_app(app)
    return limiter
