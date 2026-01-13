"""Compat shim: `app.services.actuaciones.catalogs.rubro` -> `app.domains.actuaciones.domains.catalogs.rubro`."""

from app.domains.actuaciones.domains.catalogs.rubro import get_rubro_o_falla

__all__ = ["get_rubro_o_falla"]

