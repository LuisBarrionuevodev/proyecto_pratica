"""Compat shim: `app.services.actuaciones.domains.domicilio` -> `app.domains.actuaciones.domains.domicilio`."""

from app.domains.actuaciones.domains.domicilio import get_or_create_domicilio

__all__ = ["get_or_create_domicilio"]

