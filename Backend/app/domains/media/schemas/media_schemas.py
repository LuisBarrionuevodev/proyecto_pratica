"""Schemas Pydantic para endpoints de Media."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domains.media.constants import (
    CATEGORIA_FOTO_ACTA,
    CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
    CATEGORIA_FOTO_INSPECCION,
    CATEGORIAS_MEDIA_HABILITADAS,
    TIPOS_DOCUMENTO_FOTO_ACTA,
    TIPOS_DOCUMENTO_FOTO_DOCUMENTACION_LOCAL,
)
from app.domains.media.utils.file_validation import (
    normalize_sha256,
    validate_content_type_allowed,
    validate_image_content_type,
)

TipoDocumentoFotoActa = Literal["ACTA_INSPECCION", "ACTA_NOTIFICACION", "OTRO_ACTA"]
TipoDocumentoFotoLocal = Literal[
    "HABILITACION",
    "CARNET_MANIPULADOR",
    "CERTIFICADO_DESINFECCION",
    "OTRO_DOCUMENTO_LOCAL",
]


class UploadIntentIn(BaseModel):
    """Body de POST upload-intents."""

    categoria: Literal[
        "FOTO_ACTA",
        "FOTO_DOCUMENTACION_LOCAL",
        "FOTO_INSPECCION",
    ]
    tipo_documento: Optional[TipoDocumentoFotoActa | TipoDocumentoFotoLocal] = None
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=128)
    byte_size: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)

    @field_validator("content_type")
    @classmethod
    def normalize_ct(cls, v: str) -> str:
        return (v or "").strip().lower()

    @field_validator("sha256")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        return normalize_sha256(v)

    @model_validator(mode="after")
    def validate_categoria_y_tipo(self) -> UploadIntentIn:
        if self.categoria not in CATEGORIAS_MEDIA_HABILITADAS:
            raise ValueError("categoria inválida.")
        if self.categoria == CATEGORIA_FOTO_INSPECCION:
            validate_image_content_type(self.content_type)
            if self.tipo_documento is not None:
                raise ValueError("tipo_documento no aplica a FOTO_INSPECCION.")
        else:
            validate_content_type_allowed(self.content_type)
            if self.tipo_documento is not None:
                if self.categoria == CATEGORIA_FOTO_ACTA:
                    if self.tipo_documento not in TIPOS_DOCUMENTO_FOTO_ACTA:
                        raise ValueError("tipo_documento no válido para FOTO_ACTA.")
                elif self.categoria == CATEGORIA_FOTO_DOCUMENTACION_LOCAL:
                    if self.tipo_documento not in TIPOS_DOCUMENTO_FOTO_DOCUMENTACION_LOCAL:
                        raise ValueError("tipo_documento no válido para FOTO_DOCUMENTACION_LOCAL.")
        return self


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
