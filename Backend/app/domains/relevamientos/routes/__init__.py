from __future__ import annotations

from flask import Blueprint

relevamiento = Blueprint("relevamientos", __name__)

from . import create  # noqa: E402,F401
from . import update  # noqa: E402,F401
from . import delete  # noqa: E402,F401
from . import list  # noqa: E402,F401
from . import list_operativa  # noqa: E402,F401
from . import pendientes  # noqa: E402,F401

__all__ = ["relevamiento"]
