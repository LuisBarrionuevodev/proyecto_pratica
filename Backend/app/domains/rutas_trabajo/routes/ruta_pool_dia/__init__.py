from __future__ import annotations

from flask import Blueprint

ruta_pool_dia = Blueprint("ruta_pool_dia", __name__)

from . import list_pool  # noqa: E402,F401
from . import create_pool  # noqa: E402,F401
from . import delete_pool  # noqa: E402,F401
from . import liberar_pool  # noqa: E402,F401

__all__ = ["ruta_pool_dia"]
