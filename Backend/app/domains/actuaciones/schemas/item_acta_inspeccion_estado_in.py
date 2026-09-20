"""Schema compartido para ítems de checklist (ESTADO o SI_NO)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EstadoItemInspeccion = Literal["BIEN", "OBSERVADO"]


class ItemActaInspeccionEstadoIn(BaseModel):
    """Un ítem de checklist con exactamente una respuesta persistible."""

    model_config = ConfigDict(extra="forbid")

    item_id: int = Field(..., ge=1)
    estado: Optional[EstadoItemInspeccion] = None
    valor_si_no: Optional[bool] = None

    @field_validator("estado", mode="before")
    @classmethod
    def normalize_estado(cls, v: Any) -> Any:
        if v is None or (isinstance(v, str) and not str(v).strip()):
            return None
        s = str(v).strip().upper()
        if s not in ("BIEN", "OBSERVADO"):
            raise ValueError("estado debe ser BIEN u OBSERVADO.")
        return s

    @field_validator("valor_si_no", mode="before")
    @classmethod
    def normalize_valor_si_no(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("true", "1", "si", "sí"):
                return True
            if s in ("false", "0", "no"):
                return False
        raise ValueError("valor_si_no debe ser booleano.")

    @model_validator(mode="after")
    def exactly_one_respuesta(self) -> ItemActaInspeccionEstadoIn:
        has_estado = self.estado is not None
        has_si_no = self.valor_si_no is not None
        if has_estado and has_si_no:
            raise ValueError(
                "Cada ítem debe enviar solo estado o valor_si_no, no ambos."
            )
        if not has_estado and not has_si_no:
            raise ValueError(
                "Cada ítem debe incluir estado (BIEN/OBSERVADO) o valor_si_no (true/false)."
            )
        return self
