"""
GEO-PERF.1 — encolar geocode post-commit tras grid commit sin bloquear HTTP.
"""

from __future__ import annotations

from typing import Iterable, List

from app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service import (
    enqueue_geocode_post_commit,
)
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_worker import (
    flush_geocode_post_commit_queue_sync,
    geocode_post_commit_async_enabled,
    schedule_geocode_post_commit_drain,
)


def schedule_geocode_after_grid_commit(domicilio_ids: Iterable[int]) -> List[int]:
    """
    Encola geocode para domicilios afectados y dispara worker controlado.

    En modo sync (tests / GEO_POST_COMMIT_ASYNC=false) procesa la cola inmediatamente.

    Args:
        domicilio_ids: ids deduplicables del lote commit.

    Returns:
        domicilio_id encolados.
    """
    enqueued = enqueue_geocode_post_commit(domicilio_ids)
    if not enqueued:
        return []

    if geocode_post_commit_async_enabled():
        schedule_geocode_post_commit_drain()
    else:
        flush_geocode_post_commit_queue_sync()
    return enqueued
