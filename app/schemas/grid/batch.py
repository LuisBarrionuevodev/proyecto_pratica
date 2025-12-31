from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StartBatchResponse(BaseModel):
    batch_id: UUID


class ValidateRowRequest(BaseModel):
    batch_id: UUID
    row_id: str = Field(..., min_length=1)
    row: Dict[str, Any]  # raw row


class ValidateRowResponse(BaseModel):
    batch_id: UUID
    row_id: str
    ok: bool
    errors: Dict[str, str] = Field(default_factory=dict)
    normalized: Optional[Dict[str, Any]] = None


class ValidateBatchRequest(BaseModel):
    batch_id: UUID
    rows: List[Dict[str, Any]]  # cada item: {"row_id": "...", "row": {...}}


class ValidateBatchResponse(BaseModel):
    batch_id: UUID
    results: List[ValidateRowResponse]
