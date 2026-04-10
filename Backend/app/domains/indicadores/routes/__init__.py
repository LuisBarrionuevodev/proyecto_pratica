from __future__ import annotations

from flask import Blueprint

indicadores_api = Blueprint("indicadores_api", __name__)

from . import resumen  # noqa: E402,F401

__all__ = ["indicadores_api"]
