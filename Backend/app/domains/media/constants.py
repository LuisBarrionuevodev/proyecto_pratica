"""Constantes de categorías y tipos MIME permitidos en Media."""

from __future__ import annotations

CATEGORIA_FOTO_ACTA = "FOTO_ACTA"
CATEGORIA_FOTO_DOCUMENTACION_LOCAL = "FOTO_DOCUMENTACION_LOCAL"
CATEGORIA_FOTO_INSPECCION = "FOTO_INSPECCION"

CATEGORIAS_MEDIA_0A_HABILITADAS = frozenset(
    {
        CATEGORIA_FOTO_ACTA,
        CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
    }
)

TIPOS_DOCUMENTO_FOTO_ACTA = frozenset(
    {
        "ACTA_INSPECCION",
        "ACTA_NOTIFICACION",
        "OTRO_ACTA",
    }
)

TIPOS_DOCUMENTO_FOTO_DOCUMENTACION_LOCAL = frozenset(
    {
        "HABILITACION",
        "CARNET_MANIPULADOR",
        "CERTIFICADO_DESINFECCION",
        "OTRO_DOCUMENTO_LOCAL",
    }
)

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
