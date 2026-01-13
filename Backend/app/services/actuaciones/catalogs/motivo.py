"""Compat shim: `app.services.actuaciones.catalogs.motivo` -> `app.domains.actuaciones.domains.catalogs.motivo`."""

from app.domains.actuaciones.domains.catalogs.motivo import get_motivo_o_falla

__all__ = ["get_motivo_o_falla"]

