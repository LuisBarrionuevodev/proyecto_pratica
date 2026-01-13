"""Compat shim: `app.services.actuaciones.create_service` -> `app.domains.actuaciones.services.create_service`."""

from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload

__all__ = ["crear_actuacion_desde_payload"]

