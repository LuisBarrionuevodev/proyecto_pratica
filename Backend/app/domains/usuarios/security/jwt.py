from __future__ import annotations

import os
from datetime import timedelta

from flask import Flask
from flask_jwt_extended import JWTManager

jwt = JWTManager()

# Flask-JWT-Extended 4.x: si no se define JWT_ACCESS_TOKEN_EXPIRES, el default del
# library es timedelta(minutes=15) — demasiado corto para uso operativo en SPA.
_DEFAULT_ACCESS_MINUTES = 480  # 8 h
_MIN_ACCESS_MINUTES = 5


def _resolve_access_token_minutes() -> int:
    raw = os.getenv("JWT_ACCESS_TOKEN_MINUTES", "").strip()
    if raw:
        try:
            n = int(raw)
            if n >= _MIN_ACCESS_MINUTES:
                return n
            if n > 0:
                return _MIN_ACCESS_MINUTES
        except ValueError:
            pass
    return _DEFAULT_ACCESS_MINUTES


def init_jwt(app: Flask) -> None:
    """
    Inicializa Flask-JWT-Extended y defaults de configuración.

    TTL del access token: ``JWT_ACCESS_TOKEN_MINUTES`` (env), por defecto 480 (8 h).
    El valor efectivo se registra en log al arrancar la app.

    Args:
        app: aplicación Flask.
    """
    app.config.setdefault("JWT_SECRET_KEY", "dev-change-this-secret")
    token_minutes = _resolve_access_token_minutes()
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=token_minutes)
    jwt.init_app(app)
    app.logger.info(
        "JWT access token TTL configurado: %s minutos (env JWT_ACCESS_TOKEN_MINUTES; "
        "default librería sin config: 15 min).",
        token_minutes,
    )

