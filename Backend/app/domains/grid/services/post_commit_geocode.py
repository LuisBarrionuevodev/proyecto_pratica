"""
GEO-PERF.1 — encolar geocode post-commit tras grid commit sin bloquear HTTP.
"""

from __future__ import annotations

import logging
from typing import Iterable, List

from app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service import (
    enqueue_geocode_post_commit,
)
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_worker import (
    flush_geocode_post_commit_queue_sync,
    geocode_post_commit_async_enabled,
    schedule_geocode_post_commit_drain,
)

logger = logging.getLogger(__name__)


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
        outcome = schedule_geocode_post_commit_drain()
        if outcome == "scheduled":
            logger.info("GEO_DRAIN_SCHEDULED domicilio_ids=%s", enqueued)
        elif outcome == "coalesced":
            logger.info(
                "GEO_DRAIN_COALESCED reason=already_running rerun_needed=true domicilio_ids=%s",
                enqueued,
            )
        elif outcome == "executor_unavailable":
            logger.warning(
                "GEO_DRAIN_NOT_SCHEDULED reason=executor_unavailable domicilio_ids=%s",
                enqueued,
            )
        elif outcome == "executor_submit_failed":
            logger.warning(
                "GEO_DRAIN_NOT_SCHEDULED reason=executor_submit_failed domicilio_ids=%s",
                enqueued,
            )
    else:
        flush_geocode_post_commit_queue_sync()
    return enqueued
