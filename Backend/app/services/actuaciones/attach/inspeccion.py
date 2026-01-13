"""Compat shim: `app.services.actuaciones.attach.inspeccion` -> `app.domains.actuaciones.attach.inspeccion`."""

from app.domains.actuaciones.attach.inspeccion import attach_inspeccion

__all__ = ["attach_inspeccion"]

