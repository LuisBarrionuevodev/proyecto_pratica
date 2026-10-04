"""Validación de MIME, tamaño y magic bytes."""

from __future__ import annotations

import hashlib
import re

from app.domains.media.constants import (
    DOCUMENT_CONTENT_TYPES,
    IMAGE_CONTENT_TYPES,
    PDF_CONTENT_TYPE,
)

_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def normalize_sha256(value: str) -> str:
    """
    Valida formato hex de 64 caracteres.

    Errores:
        ValueError: formato inválido.
    """
    s = (value or "").strip().lower()
    if not _SHA256_RE.match(s):
        raise ValueError("sha256 debe ser hexadecimal de 64 caracteres.")
    return s


def validate_content_type_allowed(content_type: str) -> str:
    """
    Valida MIME permitido para documentación.

    Retorno:
        MIME en minúsculas.

    Errores:
        ValueError: MIME no permitido.
    """
    ct = (content_type or "").strip().lower()
    if ct not in DOCUMENT_CONTENT_TYPES:
        raise ValueError("content_type no permitido para documentación.")
    return ct


def max_bytes_for_content_type(content_type: str, *, max_image: int, max_document: int) -> int:
    """Devuelve el límite de bytes según PDF vs imagen."""
    if content_type == PDF_CONTENT_TYPE:
        return max_document
    if content_type in IMAGE_CONTENT_TYPES:
        return max_image
    raise ValueError("content_type sin límite configurado.")


def verify_magic_bytes(content_type: str, data: bytes) -> None:
    """
    Verifica firma mínima del archivo.

    Errores:
        ValueError: magic bytes no coinciden con el MIME declarado.
    """
    if not data:
        raise ValueError("Archivo vacío.")
    if content_type == PDF_CONTENT_TYPE:
        if not data.startswith(b"%PDF"):
            raise ValueError("El archivo no parece un PDF válido.")
        return
    if content_type == "image/jpeg":
        if not data.startswith(b"\xff\xd8\xff"):
            raise ValueError("El archivo no parece un JPEG válido.")
        return
    if content_type == "image/png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("El archivo no parece un PNG válido.")
        return
    if content_type == "image/webp":
        if len(data) < 12 or data[0:4] != b"RIFF" or data[8:12] != b"WEBP":
            raise ValueError("El archivo no parece un WebP válido.")
        return
    raise ValueError("content_type sin validación de magic bytes.")


def sha256_hex(data: bytes) -> str:
    """Calcula SHA-256 en hex minúsculas."""
    return hashlib.sha256(data).hexdigest()
