"""Compat shim: `app.mappers.grid.actuacion_row_mapper` -> `app.domains.actuaciones.mappers.grid.actuacion_row_mapper`."""

from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row

__all__ = ["map_actuacion_row"]

