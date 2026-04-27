"""Schemas de entrada para edición del expediente de prórroga (notificación)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class NotificacionProrrogaExpedientePatchIn(BaseModel):
    """
    Actualiza número, fecha y plazo otorgado (días hábiles de prórroga) de un expediente
    ``PRORROGA_NOTIFICACION`` ya existente.
    """

    numero_expediente: str = Field(..., min_length=1, max_length=32)
    fecha_expediente: date
    plazo_otorgado: int = Field(..., ge=0, description="Días de prórroga otorgados en este expediente.")
