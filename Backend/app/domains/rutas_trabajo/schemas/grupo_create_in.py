from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RutaGrupoCreateIn(BaseModel):
    """
    Valida la creación de grupo dentro de una ruta en borrador.
    """

    nombre: Optional[str] = Field(default=None, min_length=1, max_length=120)
    estado: Optional[str] = Field(default=None, max_length=32)

    @field_validator("nombre")
    @classmethod
    def normalize_nombre(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        value = v.strip()
        if not value:
            raise ValueError("nombre es obligatorio")
        return value

    @field_validator("estado")
    @classmethod
    def normalize_estado(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None
