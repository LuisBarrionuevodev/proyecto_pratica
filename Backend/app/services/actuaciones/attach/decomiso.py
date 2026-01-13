"""Compat shim: `app.services.actuaciones.attach.decomiso` -> `app.domains.actuaciones.attach.decomiso`."""

from app.domains.actuaciones.attach.decomiso import attach_decomiso

__all__ = ["attach_decomiso"]

