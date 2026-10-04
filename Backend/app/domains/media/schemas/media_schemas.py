"""Schemas Pydantic para endpoints de Media."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.domains.media.constants import CATEGORIA_ACTA_DOCUMENTACION, CATEGORIA_FOTO_INSPECCION
from app.domains.media.utils.file_validation import normalize_sha256, validate_content_type_allowed


class UploadIntentIn(BaseModel):
    """Body de POST upload-intents."""

    categoria: Literal["ACTA_DOCUMENTACION", "FOTO_INSPECCION"]
    tipo_documento: Optional[
        Literal["ACTA_INSPECCION", "ACTA_NOTIFICACION", "OTRO_DOCUMENTO"]
    ] = None
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=128)
    byte_size: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)

    @field_validator("content_type")
    @classmethod
    def validate_ct(cls, v: str) -> str:
        return validate_content_type_allowed(v)

    @field_validator("sha256")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        return normalize_sha256(v)

    @field_validator("categoria")
    @classmethod
    def validate_categoria_media0(cls, v: str) -> str:
        if v != CATEGORIA_ACTA_DOCUMENTACION:
            if v == CATEGORIA_FOTO_INSPECCION:
                raise ValueError("FOTO_INSPECCION no está habilitada en esta versión.")
            raise ValueError("categoria inválida.")
        return v


class UploadIntentOut(BaseModel):
    """Respuesta de intención de carga."""

    archivo_id: int
    upload_url: str
    expires_at: datetime


class CompleteUploadOut(BaseModel):
    """Respuesta de confirmación exitosa."""

    archivo_id: int
    status: Literal["READY"]
    uploaded_at: datetime


class DownloadUrlOut(BaseModel):
    """URL temporal de descarga."""

    download_url: str
    expires_at: datetime
