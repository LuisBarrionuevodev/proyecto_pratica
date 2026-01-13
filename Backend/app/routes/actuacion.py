"""Compat: mantiene el import del blueprint `actuacion`.

El blueprint real vive en `app.domains.actuaciones.routes`.
"""

from __future__ import annotations

from app.domains.actuaciones.routes import actuacion  # noqa: F401

__all__ = ["actuacion"]
