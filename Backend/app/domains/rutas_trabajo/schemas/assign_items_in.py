from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RutaItemsAssignIn(BaseModel):
    """
    Valida asignación bulk de iniciadores a un grupo.
    """

    iniciador_ids: list[int] = Field(min_length=1)

    @field_validator("iniciador_ids")
    @classmethod
    def validate_iniciador_ids(cls, v: list[int]) -> list[int]:
        cleaned: list[int] = []
        seen: set[int] = set()
        for raw in v:
            value = int(raw)
            if value <= 0:
                raise ValueError("iniciador_ids contiene valores inválidos")
            if value in seen:
                continue
            seen.add(value)
            cleaned.append(value)
        if not cleaned:
            raise ValueError("Debe enviar al menos un iniciador")
        return cleaned
