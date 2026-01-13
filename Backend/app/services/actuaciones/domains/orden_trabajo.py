"""Compat shim: `app.services.actuaciones.domains.orden_trabajo` -> `app.domains.actuaciones.domains.orden_trabajo`."""

from app.domains.actuaciones.domains.orden_trabajo import get_or_create_orden_trabajo

__all__ = ["get_or_create_orden_trabajo"]

