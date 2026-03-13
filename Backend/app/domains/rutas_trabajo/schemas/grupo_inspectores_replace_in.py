from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RutaGrupoInspectoresReplaceIn(BaseModel):
    """
    Valida reemplazo total de inspectores de un grupo.
    """

    inspector_ids: list[int] = Field(default_factory=list)

    @field_validator("inspector_ids")
    @classmethod
    def validate_ids(cls, v: list[int]) -> list[int]:
        cleaned: list[int] = []
        seen: set[int] = set()
        for item in v:
            value = int(item)
            if value <= 0:
                raise ValueError("inspector_ids contiene valores inválidos")
            if value in seen:
                continue
            seen.add(value)
            cleaned.append(value)
        return cleaned
