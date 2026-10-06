"""Errores operativos de Media (códigos estables para el cliente)."""

from __future__ import annotations


class MediaDomainError(ValueError):
    """
    Error de negocio de carga de archivos.

    Parámetros:
        code: identificador estable (p. ej. MEDIA_QUOTA_EXCEEDED).
        message: texto legible para UI.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


MEDIA_QUOTA_EXCEEDED = "MEDIA_QUOTA_EXCEEDED"
MEDIA_MIME_UNSUPPORTED = "MEDIA_MIME_UNSUPPORTED"
MEDIA_SIZE_EXCEEDED = "MEDIA_SIZE_EXCEEDED"
MEDIA_OBJECT_MISSING = "MEDIA_OBJECT_MISSING"
MEDIA_SHA_MISMATCH = "MEDIA_SHA_MISMATCH"
MEDIA_STATE_INVALID = "MEDIA_STATE_INVALID"


def media_error_json(exc: MediaDomainError) -> dict[str, str]:
    """Payload JSON 422 con código operativo."""
    return {"code": exc.code, "detail": str(exc)}


def map_value_error_to_media(exc: ValueError) -> MediaDomainError:
    """Mapea mensajes legacy a códigos MEDIA_*."""
    msg = str(exc)
    lower = msg.lower()
    if "máximo de archivos" in lower or "cupo" in lower:
        return MediaDomainError(MEDIA_QUOTA_EXCEEDED, msg)
    if "mime" in lower or "tipo" in lower and "archivo" in lower:
        return MediaDomainError(MEDIA_MIME_UNSUPPORTED, msg)
    if "byte_size" in lower or "tamaño" in lower or "límite" in lower:
        return MediaDomainError(MEDIA_SIZE_EXCEEDED, msg)
    if "no se encontró el archivo" in lower or "object" in lower and "missing" in lower:
        return MediaDomainError(MEDIA_OBJECT_MISSING, msg)
    if "sha-256" in lower or "hash" in lower:
        return MediaDomainError(MEDIA_SHA_MISMATCH, msg)
    if "estado" in lower or "pending" in lower:
        return MediaDomainError(MEDIA_STATE_INVALID, msg)
    return MediaDomainError(MEDIA_STATE_INVALID, msg)
