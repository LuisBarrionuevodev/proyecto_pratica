from __future__ import annotations

from flask import Flask
from flask_jwt_extended import JWTManager


jwt = JWTManager()


def init_jwt(app: Flask) -> None:
    """
    Inicializa Flask-JWT-Extended y defaults de configuración.

    Args:
        app: aplicación Flask.
    """
    app.config.setdefault("JWT_SECRET_KEY", "dev-change-this-secret")
    jwt.init_app(app)

