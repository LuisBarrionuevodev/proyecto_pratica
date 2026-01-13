"""Compat shim: `app.services.actuaciones.attach.expediente` -> `app.domains.actuaciones.attach.expediente`."""

from app.domains.actuaciones.attach.expediente import attach_expediente

__all__ = ["attach_expediente"]

