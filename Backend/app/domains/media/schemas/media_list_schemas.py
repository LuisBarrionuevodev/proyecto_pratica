"""Schemas de listado y eliminación de archivos."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ArchivoListItemOut(BaseModel):
    """Metadata pública de un archivo READY (sin object_key ni URLs)."""

    archivo_id: int
    original_filename: str
    content_type: str
    byte_size: int
    uploaded_at: datetime
    tipo_documento: Optional[str] = None
    categoria: Literal["FOTO_ACTA", "FOTO_DOCUMENTACION_LOCAL", "FOTO_INSPECCION"]


class RutaItemArchivosListOut(BaseModel):
    """Listado autorizado por categorías de galería RutaItem."""

    foto_acta: list[ArchivoListItemOut]
    foto_documentacion_local: list[ArchivoListItemOut]
    foto_inspeccion: list[ArchivoListItemOut]


class ArchivoDeleteOut(BaseModel):
    """Confirmación de baja lógica."""

    archivo_id: int
    status: Literal["DELETED"]
