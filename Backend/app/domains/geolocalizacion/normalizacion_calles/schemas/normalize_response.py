from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class NormalizeCalleResponse(BaseModel):
    """
    Response estándar para normalización de calles.
    """
    ok: bool
    status: str
    canon: Optional[str] = None
    score: Optional[float] = None
    error: Optional[str] = None
    suggestions: Optional[list[dict]] = None
    domicilio_id: int
