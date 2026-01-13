"""Compat shim: `app.services.actuaciones.domains.contribuyente` -> `app.domains.actuaciones.domains.contribuyente`."""

from app.domains.actuaciones.domains.contribuyente import resolve_contribuyente

__all__ = ["resolve_contribuyente"]

