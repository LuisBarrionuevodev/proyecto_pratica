"""Compat shim: `app.services.actuaciones.delete_service` -> `app.domains.actuaciones.services.delete_service`."""

from app.domains.actuaciones.services.delete_service import eliminar_actuacion

__all__ = ["eliminar_actuacion"]

