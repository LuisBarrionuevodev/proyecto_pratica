from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class OrdenTrabajoSecuenciaPatchIn(BaseModel):
    """Payload para adelantar contador OT (solo admin)."""

    new_value: int = Field(..., ge=0)
    reason: str

    @field_validator("reason", mode="before")
    @classmethod
    def _reason_no_vacio(cls, v: object) -> str:
        s = str(v or "").strip()
        if not s:
            raise ValueError("reason es obligatorio")
        if len(s) > 500:
            raise ValueError("reason demasiado largo (máx 500)")
        return s
