"""Filtros GET /actuaciones/pendientes-notificacion (OPER-RUTA.3)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator


class PendientesNotificacionFilters(BaseModel):
    """
    Filtros opcionales de la cola operativa de reinspección por notificación.

    Parámetros:
        desde, hasta: rango sobre ``Actuaciones.fecha`` (fecha de la inspección base).
        numero_notificacion: subcadena sobre ``Notificacion.numero_acta``.
    """

    desde: Optional[date] = None
    hasta: Optional[date] = None
    numero_notificacion: Optional[str] = None
    calle_q: Optional[str] = None
    orden_trabajo: Optional[str] = None

    @field_validator("numero_notificacion", "calle_q", "orden_trabajo")
    @classmethod
    def _strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s or None
