"""Compat shim: `app.services.actuaciones.attach.comprobacion` -> `app.domains.actuaciones.attach.comprobacion`."""

from app.domains.actuaciones.attach.comprobacion import attach_comprobacion

__all__ = ["attach_comprobacion"]

