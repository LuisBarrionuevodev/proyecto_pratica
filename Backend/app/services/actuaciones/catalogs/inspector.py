"""Compat shim: `app.services.actuaciones.catalogs.inspector` -> `app.domains.actuaciones.domains.catalogs.inspector`."""

from app.domains.actuaciones.domains.catalogs.inspector import get_inspectores_o_falla

__all__ = ["get_inspectores_o_falla"]

