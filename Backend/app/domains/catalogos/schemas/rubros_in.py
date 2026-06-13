"""Schemas de catálogo de rubros (STAB-8)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RubrosCatalogIn(BaseModel):
    """Parámetros GET /catalogos/rubros."""

    q: Optional[str] = Field(None, max_length=120)
    limit: int = Field(500, ge=1, le=500)

    @field_validator("q")
    @classmethod
    def strip_q(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s or None
