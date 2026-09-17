"""
GEO-PERF.1 / 1.1 — worker controlado para drenar la cola de geocode post-commit.

Usa ThreadPoolExecutor (1 worker) con app context; no ``threading.Thread`` sueltos.
Los trabajos persisten en DB y sobreviven reinicios del proceso.
"""

from __future__ import annotations

import atexit
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from flask import Flask
from sqlalchemy import inspect
from sqlalchemy.exc import ProgrammingError

from app.database import db
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service import (
    count_recoverable_geocode_post_commit_jobs,
    process_geocode_post_commit_jobs,
    reclaim_stale_processing_jobs,
)

logger = logging.getLogger(__name__)

_executor: Optional[ThreadPoolExecutor] = None
_app: Optional[Flask] = None
_drain_lock = threading.Lock()
_drain_scheduled = False
_shutdown_registered = False


def geocode_post_commit_async_enabled() -> bool:
    """True si el procesamiento async está habilitado (default: sí)."""
    return os.getenv("GEO_POST_COMMIT_ASYNC", "true").lower() in {"1", "true", "yes", "on"}


def _is_werkzeug_reloader_parent() -> bool:
    """
    True solo en el supervisor del reloader de Werkzeug (no sirve la app).

    GEO-PERF.1.3: ``FLASK_DEBUG=1`` sin reloader (waitress, IDE, ``--no-reload``)
    NO debe bloquear el worker. Solo se omite init cuando Werkzeug marca explícitamente
    el proceso supervisor vía ``WERKZEUG_RUN_MAIN=false``.
    """
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return False
    return os.environ.get("WERKZEUG_RUN_MAIN") == "false"


def init_geocode_post_commit_worker(app: Flask) -> None:
    """
    Inicializa executor controlado y programa drenado de jobs pendientes al arranque.

    Args:
        app: instancia Flask.
    """
    global _executor, _app, _shutdown_registered

    if not geocode_post_commit_async_enabled():
        return
    if _is_werkzeug_reloader_parent():
        logger.debug("geocode_post_commit_worker skip init in werkzeug reloader parent")
        return
    if _executor is not None:
        return

    _app = app
    max_workers = max(1, int(os.getenv("GEO_POST_COMMIT_WORKER_THREADS", "1")))
    _executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="geocode-post-commit")
    if not _shutdown_registered:
        atexit.register(shutdown_geocode_post_commit_worker)
        _shutdown_registered = True

    with app.app_context():
        try:
            if not inspect(db.engine).has_table("geocode_post_commit_job"):
                return
            reclaimed = reclaim_stale_processing_jobs()
            if reclaimed:
                logger.info("geocode_post_commit_worker startup reclaimed=%s", reclaimed)
            recoverable = count_recoverable_geocode_post_commit_jobs()
            if recoverable > 0:
                schedule_geocode_post_commit_drain()
        except ProgrammingError:
            logger.warning("geocode_post_commit_job table missing; skip startup drain")
        finally:
            db.session.remove()


def shutdown_geocode_post_commit_worker() -> None:
    """
    Cierra el executor al terminar el proceso.

    Jobs en ``processing`` quedan con lease; se recuperan al reiniciar vía
    ``reclaim_stale_processing_jobs``.
    """
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
        _executor = None
        logger.info(
            "geocode_post_commit_worker executor shutdown (jobs processing recoverable via lease)"
        )


def schedule_geocode_post_commit_drain(limit: Optional[int] = None) -> bool:
    """
    Programa drenado de la cola en el executor controlado.

    Returns:
        True si se programó una corrida; False si async deshabilitado o ya programada.
    """
    global _drain_scheduled

    if not geocode_post_commit_async_enabled():
        return False
    if _executor is None or _app is None:
        logger.debug(
            "geocode_post_commit_worker drain not scheduled: executor=%s app=%s",
            _executor is not None,
            _app is not None,
        )
        return False

    with _drain_lock:
        if _drain_scheduled:
            return False
        _drain_scheduled = True

    batch_limit = int(limit or os.getenv("GEO_POST_COMMIT_DRAIN_LIMIT", "50"))

    def _run() -> None:
        global _drain_scheduled
        try:
            assert _app is not None
            with _app.app_context():
                while True:
                    summary = process_geocode_post_commit_jobs(limit=batch_limit)
                    if summary.get("claimed", 0) == 0:
                        break
        except Exception:
            logger.exception("geocode_post_commit_worker drain failed")
        finally:
            db.session.remove()
            with _drain_lock:
                _drain_scheduled = False

    _executor.submit(_run)
    return True


def flush_geocode_post_commit_queue_sync(limit: int = 50) -> dict:
    """
    Procesa la cola de forma síncrona (tests / modo sin async).

    Returns:
        Resumen de ``process_geocode_post_commit_jobs``.
    """
    try:
        return process_geocode_post_commit_jobs(limit=limit)
    finally:
        db.session.remove()
