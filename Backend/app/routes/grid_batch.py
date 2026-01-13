"""Compat shim: `app.routes.grid_batch` -> `app.domains.grid.routes`."""

from __future__ import annotations

from app.domains.grid.routes import grid as bp  # mantiene el nombre histórico `bp`

__all__ = ["bp"]

