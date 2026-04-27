"""Schemas de entrada para edición documental de comprobación (expediente envío / oficio)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ComprobacionExpedienteEnvioPatchIn(BaseModel):
    """Corrige número y fecha del expediente de envío (``ENVIO_ACTA``, sin oficio)."""

    numero_expediente: str = Field(..., min_length=1, max_length=32)
    fecha_expediente: date


class ComprobacionOficioBloquePatchIn(BaseModel):
    """Actualiza oficio y expediente de respuesta vinculado."""

    numero_oficio: str = Field(..., min_length=1, max_length=64)
    fecha_oficio: date
    juzgado_id: int = Field(..., ge=1)
    causa: Optional[str] = Field(None, max_length=255)
    numero_expediente_respuesta: str = Field(..., min_length=1, max_length=32)
    fecha_expediente_respuesta: date
