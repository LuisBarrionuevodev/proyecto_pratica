"""Limpieza de cargas PENDING abandonadas (>24 h)."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.database import db
from app.domains.media.services.media_storage_service import MediaStorageService
from app.models import Archivo


def cleanup_pending_media(*, older_than_hours: int = 24) -> int:
    """
    Borra objetos huérfanos y marca registros como DELETED.

    Parámetros:
        older_than_hours: antigüedad mínima en horas (default 24).

    Retorno:
        Cantidad de registros procesados.

    Errores:
        Ninguno; ignora fallos puntuales de delete en bucket.
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
        return 0
    storage = MediaStorageService()
    count = 0
    now = datetime.utcnow()
    for arch in rows:
        try:
            storage.delete_object(arch.object_key)
        except Exception:
            pass
        arch.status = "DELETED"
        arch.deleted_at = now
        count += 1
    db.session.commit()
    return count
