"""Generación segura de object_key (solo backend)."""

from __future__ import annotations

import re
import uuid

from app.domains.media.constants import (
    CATEGORIA_FOTO_ACTA,
    CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
    CATEGORIA_FOTO_INSPECCION,
    PDF_CONTENT_TYPE,
)

_CATEGORIAS_OBJECT_KEY = frozenset(
    {
        CATEGORIA_FOTO_ACTA,
        CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
        CATEGORIA_FOTO_INSPECCION,
    }
)

_CONTENT_TYPE_EXTENSION: dict[str, str] = {
    PDF_CONTENT_TYPE: "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

_FILENAME_FORBIDDEN = re.compile(
    r"[\\/]|\.{2,}|[\x00-\x1f]|[\u0000-\u001f]",
)


def safe_extension_for_content_type(content_type: str) -> str:
    """
    Resuelve extensión permitida a partir del MIME validado.

    Parámetros:
        content_type: MIME normalizado.

    Retorno:
        Extensión sin punto.

    Errores:
        ValueError: MIME sin extensión mapeada.
    """
    ext = _CONTENT_TYPE_EXTENSION.get(content_type.strip().lower())
    if not ext:
        raise ValueError("Tipo de contenido sin extensión permitida.")
    return ext


def build_object_key(
    *,
    ruta_item_id: int,
    categoria: str,
    content_type: str,
) -> str:
    """
    Arma la clave de objeto en el bucket.

    Formato:
        digitaliza/ruta-items/{id}/{categoria}/{uuid}.{ext}

    Parámetros:
        ruta_item_id: ítem de ruta ancla.
        categoria: FOTO_ACTA, FOTO_DOCUMENTACION_LOCAL o FOTO_INSPECCION.
        content_type: MIME ya validado.

    Retorno:
        object_key único sin datos personales.
    """
    if categoria not in _CATEGORIAS_OBJECT_KEY:
        raise ValueError("Categoría inválida para object_key.")
    ext = safe_extension_for_content_type(content_type)
    token = uuid.uuid4().hex
    return f"digitaliza/ruta-items/{int(ruta_item_id)}/{categoria}/{token}.{ext}"


def sanitize_original_filename(filename: str) -> str:
    """
    Normaliza el nombre original para metadata (no se usa en object_key).

    Parámetros:
        filename: nombre enviado por el cliente.

    Retorno:
        Nombre truncado y sin separadores de ruta.

    Errores:
        ValueError: nombre vacío o inválido.
    """
    name = (filename or "").strip()
    if not name:
        raise ValueError("filename es obligatorio.")
    if _FILENAME_FORBIDDEN.search(name):
        raise ValueError("filename contiene caracteres no permitidos.")
    if len(name) > 255:
        name = name[:255]
    return name
