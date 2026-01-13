"""Compat shim: `app.services.actuaciones.attach.notificacion` -> `app.domains.actuaciones.attach.notificacion`."""

from app.domains.actuaciones.attach.notificacion import attach_notificacion

__all__ = ["attach_notificacion"]

