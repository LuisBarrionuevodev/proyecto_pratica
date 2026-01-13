"""Compat: mantiene el import histórico `app.routes.actuaciones.actuacion`."""

from __future__ import annotations

from app.domains.actuaciones.routes import actuacion  # noqa: F401

__all__ = ["actuacion"]

