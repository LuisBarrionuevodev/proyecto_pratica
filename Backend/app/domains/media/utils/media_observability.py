"""Logs estructurados de Media sin datos sensibles."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("app.domains.media")


def _fmt(
    event: str,
    *,
    archivo_id: Optional[int] = None,
    ruta_item_id: Optional[int] = None,
    categoria: Optional[str] = None,
    status: Optional[str] = None,
    cause: Optional[str] = None,
    extra: Optional[str] = None,
) -> str:
    parts = [f"event={event}"]
    if archivo_id is not None:
        parts.append(f"archivo_id={int(archivo_id)}")
    if ruta_item_id is not None:
        parts.append(f"ruta_item_id={int(ruta_item_id)}")
    if categoria:
        parts.append(f"categoria={categoria}")
    if status:
        parts.append(f"status={status}")
    if cause:
        parts.append(f"cause={cause}")
    if extra:
        parts.append(extra)
    return " ".join(parts)


def log_upload_intent_created(
    *,
    archivo_id: int,
    ruta_item_id: int,
    categoria: str,
) -> None:
    logger.info(
        _fmt(
            "media_upload_intent_created",
            archivo_id=archivo_id,
            ruta_item_id=ruta_item_id,
            categoria=categoria,
            status="PENDING",
        )
    )


def log_upload_complete_ok(*, archivo_id: int, categoria: Optional[str] = None) -> None:
    logger.info(
        _fmt(
            "media_upload_complete_ok",
            archivo_id=archivo_id,
            categoria=categoria,
            status="READY",
        )
    )


def log_upload_complete_rejected(*, archivo_id: int, cause: str) -> None:
    logger.warning(
        _fmt(
            "media_upload_complete_rejected",
            archivo_id=archivo_id,
            status="REJECTED",
            cause=cause,
        )
    )


def log_archivo_delete_ok(
    *,
    archivo_id: int,
    ruta_item_id: Optional[int] = None,
    categoria: Optional[str] = None,
) -> None:
    logger.info(
        _fmt(
            "media_archivo_delete_ok",
            archivo_id=archivo_id,
            ruta_item_id=ruta_item_id,
            categoria=categoria,
            status="DELETED",
        )
    )


def log_cleanup_pending_batch(
    *,
    processed: int,
    storage_delete_errors: int,
) -> None:
    logger.info(
        _fmt(
            "media_cleanup_pending_batch",
            status="DELETED",
            extra=f"processed={processed} storage_delete_errors={storage_delete_errors}",
        )
    )


def log_storage_error(*, operation: str, cause: str, archivo_id: Optional[int] = None) -> None:
    logger.error(
        _fmt(
            "media_storage_error",
            archivo_id=archivo_id,
            cause=cause,
            extra=f"operation={operation}",
        )
    )
