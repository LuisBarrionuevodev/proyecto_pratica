"""Compat shim: `app.services.actuaciones.attach.clausura` -> `app.domains.actuaciones.attach.clausura`."""

from app.domains.actuaciones.attach.clausura import attach_clausura

__all__ = ["attach_clausura"]

