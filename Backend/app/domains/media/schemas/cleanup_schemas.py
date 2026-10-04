"""Resultados operativos de limpieza de media."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CleanupPendingMediaResult(BaseModel):
    """Métricas de una corrida de cleanup PENDING vencidos."""

    processed: int = Field(ge=0)
    storage_delete_errors: int = Field(ge=0)
    skipped_already_deleted: int = Field(ge=0, default=0)
