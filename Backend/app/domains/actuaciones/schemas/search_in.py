"""Schemas de búsqueda liviana (STAB-6)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ActuacionesSearchIn(BaseModel):
    """Parámetros GET /actuaciones/search."""

    q: str = Field(..., min_length=2, max_length=120)
    limit: int = Field(20, ge=1, le=50)

    @field_validator("q")
    @classmethod
    def strip_q(cls, v: str) -> str:
        s = (v or "").strip()
        if len(s) < 2:
            raise ValueError("Ingresá al menos 2 caracteres para buscar.")
        return s


class OrdenesSearchIn(BaseModel):
    """Parámetros GET /actuaciones/ordenes/search."""

    q: str = Field(..., min_length=1, max_length=32)
    limit: int = Field(20, ge=1, le=50)

    @field_validator("q")
    @classmethod
    def strip_q(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("Ingresá un número de orden para buscar.")
        return s
