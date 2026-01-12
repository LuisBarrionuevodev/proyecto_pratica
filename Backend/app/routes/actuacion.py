"""Compat: mantiene el import del blueprint `actuacion`.

El blueprint real vive en `app.routes.actuaciones`.
"""

from __future__ import annotations

from app.routes.actuaciones import actuacion  # noqa: F401

__all__ = ["actuacion"]
