"""Schemas de entrada para edición documental de comprobación (expediente envío / oficio)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ComprobacionExpedienteEnvioPatchIn(BaseModel):
    """Corrige número y fecha del expediente de envío (``ENVIO_ACTA``, sin oficio)."""

    numero_expediente: str = Field(..., min_length=1, max_length=32)
    fecha_expediente: date


class ComprobacionOficioBloquePatchIn(BaseModel):
    """
    Actualiza oficio y expediente de respuesta vinculado.

    **Fechas:** la fecha del expediente de respuesta sigue a la del oficio. Si no se envía
    ``fecha_expediente_respuesta`` o difiere de ``fecha_oficio``, se unifica a ``fecha_oficio``.
    """

    numero_oficio: str = Field(..., min_length=1, max_length=64)
    fecha_oficio: date
    juzgado_id: int = Field(..., ge=1)
    causa: Optional[str] = Field(None, max_length=255)
    numero_expediente_respuesta: str = Field(..., min_length=1, max_length=32)
    fecha_expediente_respuesta: Optional[date] = None

    @model_validator(mode="after")
    def _unificar_fecha_oficio_y_expediente_respuesta(self) -> "ComprobacionOficioBloquePatchIn":
        fo = self.fecha_oficio
        if self.fecha_expediente_respuesta is None or self.fecha_expediente_respuesta != fo:
            self.fecha_expediente_respuesta = fo
        return self
