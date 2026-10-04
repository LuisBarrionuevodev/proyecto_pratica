"""Tipos compartidos del adaptador de storage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ObjectHeadResult:
    """Metadata de un objeto existente en el bucket."""

    content_length: int
    content_type: str | None


@dataclass(frozen=True)
class PresignedUrlResult:
    """URL firmada temporal y vencimiento."""

    url: str
    expires_at: datetime
