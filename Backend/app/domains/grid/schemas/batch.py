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


class BatchRowItem(BaseModel):
    """Item de batch: un row_id y su row raw."""

    row_id: str = Field(..., min_length=1)
    row: Dict[str, Any]


class ValidateBatchRequest(BaseModel):
    batch_id: UUID
    rows: List[BatchRowItem]


class ValidateBatchResponse(BaseModel):
    batch_id: UUID
    results: List[ValidateRowResponse]


class CommitRowRequest(BaseModel):
    """Commit/persistencia de una fila ya validada y mapeada (payload canon)."""

    batch_id: UUID
    row_id: str = Field(..., min_length=1)
    normalized: Dict[str, Any]


class CommitRowResponse(BaseModel):
    batch_id: UUID
    row_id: str
    ok: bool
    errors: Dict[str, str] = Field(default_factory=dict)
    persisted: Optional[Dict[str, Any]] = None
