from __future__ import annotations

from flask import Blueprint

grid = Blueprint("grid_batch", __name__, url_prefix="/grid")

# Registrar endpoints (side-effect imports)
from . import batch  # noqa: E402,F401

__all__ = ["grid"]