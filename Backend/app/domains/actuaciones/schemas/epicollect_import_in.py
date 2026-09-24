"""Entrada HTTP para import EpiCollect (solo el JSON crudo del entry)."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class EpicollectImportIn(BaseModel):
    """
    Body POST import EpiCollect.

    Attributes:
        payload: objeto JSON del entry tal como lo devuelve EpiCollect / export.
    """

    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(
        ...,
        description="Entry EpiCollect5 (dict); debe contener un UUID de entry reconocible.",
    )
