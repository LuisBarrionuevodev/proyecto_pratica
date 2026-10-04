"""Constantes de categorías y tipos MIME permitidos en Media.0."""

from __future__ import annotations

CATEGORIA_ACTA_DOCUMENTACION = "ACTA_DOCUMENTACION"
CATEGORIA_FOTO_INSPECCION = "FOTO_INSPECCION"

CATEGORIAS_MEDIA_0 = frozenset({CATEGORIA_ACTA_DOCUMENTACION})

DOCUMENT_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)

IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)

PDF_CONTENT_TYPE = "application/pdf"

STORAGE_PROVIDER_RAILWAY = "railway_s3"
