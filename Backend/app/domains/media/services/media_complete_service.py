"""Caso de uso: confirmar carga (HEAD + magic bytes + SHA-256)."""

from __future__ import annotations

from datetime import datetime

from app.database import db
from app.domains.media.schemas.media_schemas import CompleteUploadOut
from app.domains.media.services.media_access_service import get_archivo_link_for_access
from app.domains.media.services.media_storage_service import MediaStorageService
from app.domains.media.utils.file_validation import (
    sha256_hex,
    verify_magic_bytes,
)
from app.models import Archivo


def _reject_archivo(arch: Archivo, storage: MediaStorageService) -> None:
    """Marca REJECTED, borra objeto y no deja el archivo disponible."""
    storage.delete_object(arch.object_key)
    arch.status = "REJECTED"
    arch.uploaded_at = None


def completar_carga_archivo(archivo_id: int) -> CompleteUploadOut:
    """
    Confirma que el objeto subido al bucket es válido y pasa a READY.

    Parámetros:
        archivo_id: PK del registro PENDING.

    Retorno:
        CompleteUploadOut.

    Errores:
        ValueError: validación fallida (422 en ruta).
        MediaAccessError / RutaItemAccessError: autorización.
    """
    arch, _link = get_archivo_link_for_access(int(archivo_id))
    if arch.status != "PENDING":
        raise ValueError("Solo se pueden confirmar archivos en estado PENDING.")

    storage = MediaStorageService()
    head = storage.head_object(arch.object_key)
    if head is None:
        _reject_archivo(arch, storage)
        db.session.commit()
        raise ValueError("No se encontró el archivo en el storage.")

    if head.content_length != int(arch.byte_size):
        _reject_archivo(arch, storage)
        db.session.commit()
        raise ValueError("El tamaño del archivo no coincide con lo declarado.")

    head_ct = (head.content_type or "").split(";", 1)[0].strip().lower()
    if head_ct and head_ct != arch.content_type:
        _reject_archivo(arch, storage)
        db.session.commit()
        raise ValueError("El tipo MIME del archivo no coincide con lo declarado.")

    body = storage.get_object_bytes(arch.object_key)
    if body is None:
        _reject_archivo(arch, storage)
        db.session.commit()
        raise ValueError("No se pudo leer el archivo para validación.")

    try:
        verify_magic_bytes(arch.content_type, body)
    except ValueError:
        _reject_archivo(arch, storage)
        db.session.commit()
        raise

    digest = sha256_hex(body)
    if digest != arch.sha256.lower():
        _reject_archivo(arch, storage)
        db.session.commit()
        raise ValueError("El hash SHA-256 no coincide con lo declarado.")

    now = datetime.utcnow()
    arch.status = "READY"
    arch.uploaded_at = now
    db.session.commit()

    return CompleteUploadOut(
        archivo_id=int(arch.id),
        status="READY",
        uploaded_at=now,
    )
