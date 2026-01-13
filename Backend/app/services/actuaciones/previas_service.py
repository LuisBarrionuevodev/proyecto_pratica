"""Compat shim: `app.services.actuaciones.previas_service` -> `app.domains.actuaciones.services.previas_service`."""

from app.domains.actuaciones.services.previas_service import resolver_previas

__all__ = ["resolver_previas"]

