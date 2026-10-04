"""Limpieza de cargas PENDING abandonadas (>24 h)."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.database import db
from app.domains.media.schemas.cleanup_schemas import CleanupPendingMediaResult
from app.domains.media.services.media_storage_service import MediaStorageService
from app.domains.media.utils.media_observability import (
    log_cleanup_pending_batch,
    log_storage_error,
)
from app.models import Archivo


def cleanup_pending_media(*, older_than_hours: int = 24) -> CleanupPendingMediaResult:
    """
    Borra objetos huérfanos y marca registros como DELETED.

    Parámetros:
        older_than_hours: antigüedad mínima en horas (default 24).

    Retorno:
        CleanupPendingMediaResult (procesados, errores de storage, omitidos).

    Errores:
        Ninguno; continúa el lote ante fallos puntuales de delete en bucket.
    """
    cutoff = datetime.utcnow() - timedelta(hours=int(older_than_hours))
    rows = (
        Archivo.query.filter(
            Archivo.status == "PENDING",
            Archivo.deleted_at.is_(None),
            Archivo.created_at < cutoff,
        )
        .order_by(Archivo.id.asc())
        .all()
    )
    if not rows:
        result = CleanupPendingMediaResult(processed=0, storage_delete_errors=0)
        log_cleanup_pending_batch(processed=0, storage_delete_errors=0)
        return result

    storage = MediaStorageService()
    processed = 0
    storage_delete_errors = 0
    skipped_already_deleted = 0
    now = datetime.utcnow()
    for arch in rows:
        if arch.status != "PENDING" or arch.deleted_at is not None:
            skipped_already_deleted += 1
            continue
        try:
            storage.delete_object(arch.object_key)
        except Exception as exc:
            storage_delete_errors += 1
            log_storage_error(
                operation="delete_object",
                cause=type(exc).__name__,
                archivo_id=int(arch.id),
            )
        arch.status = "DELETED"
        arch.deleted_at = now
        processed += 1
    db.session.commit()
    result = CleanupPendingMediaResult(
        processed=processed,
        storage_delete_errors=storage_delete_errors,
        skipped_already_deleted=skipped_already_deleted,
    )
    log_cleanup_pending_batch(
        processed=result.processed,
        storage_delete_errors=result.storage_delete_errors,
    )
    return result
