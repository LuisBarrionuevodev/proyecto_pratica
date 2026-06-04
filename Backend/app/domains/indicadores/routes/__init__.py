from __future__ import annotations

from flask import Blueprint

indicadores_api = Blueprint("indicadores_api", __name__)

from . import (  # noqa: E402,F401
    ejecutivo,
    no_realizadas,
    pendientes,
    productividad,
    resumen,
    riesgo,
)

__all__ = ["indicadores_api"]
