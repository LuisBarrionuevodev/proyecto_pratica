"""Compat shim: `app.services.actuaciones.attach.oficio` -> `app.domains.actuaciones.attach.oficio`."""

from app.domains.actuaciones.attach.oficio import attach_oficio

__all__ = ["attach_oficio"]

