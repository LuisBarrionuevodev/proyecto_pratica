"""Compat shim: `app.presenters.actuacion_presenters` -> `app.domains.actuaciones.presenters.actuacion_presenters`."""

from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row

__all__ = ["actuacion_to_grid_row"]

