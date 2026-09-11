"""Schema compartido para ítems de checklist con estado BIEN/OBSERVADO."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EstadoItemInspeccion = Literal["BIEN", "OBSERVADO"]


class ItemActaInspeccionEstadoIn(BaseModel):
    """Un ítem de checklist con estado persistible (no NONE)."""

    model_config = ConfigDict(extra="forbid")

    item_id: int = Field(..., ge=1)
    estado: EstadoItemInspeccion

    @field_validator("estado", mode="before")
    @classmethod
    def normalize_estado(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("estado es obligatorio.")
        s = str(v).strip().upper()
        if s not in ("BIEN", "OBSERVADO"):
            raise ValueError("estado debe ser BIEN u OBSERVADO.")
        return s
