"""Entrada HTTP: import desde API EpiCollect (solo ec5_uuid)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EpicollectImportFromApiIn(BaseModel):
    """
    Body POST: traer entry remoto y ejecutar el import ya existente sobre la actuación.

    Attributes:
        ec5_uuid: UUID del entry en EpiCollect (mismo que persiste en ``actuaciones.ec5_uuid``).
    """

    model_config = ConfigDict(extra="forbid")

    ec5_uuid: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="UUID del entry EC5 (formato con guiones preferido).",
    )
