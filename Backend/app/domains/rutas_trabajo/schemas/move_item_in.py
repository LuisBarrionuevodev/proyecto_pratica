from __future__ import annotations

from pydantic import BaseModel, Field


class RutaItemMoveIn(BaseModel):
    """
    Valida movimiento de item entre grupos.
    """

    target_grupo_id: int = Field(ge=1)
