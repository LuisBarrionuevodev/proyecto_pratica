"""Compat shim: `app.services.actuaciones.update_service` -> `app.domains.actuaciones.services.update_service`."""

from app.domains.actuaciones.services.update_service import _get_actuacion_or_404, actualizar_actuacion

__all__ = ["_get_actuacion_or_404", "actualizar_actuacion"]

