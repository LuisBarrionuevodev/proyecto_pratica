"""
GEO-PERF.1 / 1.1 / 2 / 2.1 — worker controlado para drenar la cola de geocode post-commit.

Usa ThreadPoolExecutor (1 worker) con app context; no ``threading.Thread`` sueltos.
Los trabajos persisten en DB y sobreviven reinicios del proceso.
"""

from __future__ import annotations

import atexit
import logging
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Literal, Optional

from flask import Flask
from sqlalchemy import inspect
from sqlalchemy.exc import ProgrammingError

from app.database import db
from app.domains.geolocalizacion.geocode.services.geocode_post_commit_queue_service import (
    count_pending_geocode_post_commit_jobs,
    count_recoverable_geocode_post_commit_jobs,
    process_geocode_post_commit_jobs,
    reclaim_stale_processing_jobs,
)

logger = logging.getLogger(__name__)

DrainScheduleOutcome = Literal[
    "scheduled",
    "coalesced",
    "async_disabled",
    "executor_unavailable",
    "executor_submit_failed",
]

_executor: Optional[ThreadPoolExecutor] = None
_app: Optional[Flask] = None
_drain_lock = threading.Lock()
_drain_scheduled = False
_drain_rerun_needed = False
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


def _configure_geocode_worker_logging() -> None:
    """
    Ajusta nivel del logger del worker según ``LOG_LEVEL`` (solo este módulo).

    Para ver trazas GEO_DRAIN_* en desarrollo sin cambiar el root logger:
    ``LOG_LEVEL=INFO`` o ``LOG_LEVEL=DEBUG``.
    """
    level_name = os.getenv("LOG_LEVEL", "").strip().upper()
    if level_name in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        level = getattr(logging, level_name)
        logger.setLevel(level)
        logging.getLogger("app.domains.grid.services.post_commit_geocode").setLevel(level)


def _on_drain_future_done(future: Future) -> None:
    """Callback del Future de drain: loguea excepciones no observadas en el thread."""
    try:
        exc = future.exception()
        if exc is not None:
            logger.error(
                "GEO_DRAIN_FUTURE_FAILED error=%s",
                exc,
                exc_info=exc,
            )
        else:
            logger.debug("GEO_DRAIN_FUTURE_DONE")
    except Exception:
        logger.exception("GEO_DRAIN_FUTURE_CALLBACK_FAILED")


def init_geocode_post_commit_worker(app: Flask) -> None:
    """
    Inicializa executor controlado y programa drenado de jobs pendientes al arranque.

    Args:
        app: instancia Flask.
    """
    global _executor, _app, _shutdown_registered, _drain_scheduled, _drain_rerun_needed

    _configure_geocode_worker_logging()

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
    with _drain_lock:
        _drain_scheduled = False
        _drain_rerun_needed = False
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
    ``reclaim_stale_processing_jobs``. Resetea flags para que un init posterior
    no herede estado del worker anterior.
    """
    global _executor, _drain_scheduled, _drain_rerun_needed

    executor = _executor
    with _drain_lock:
        _drain_scheduled = False
        _drain_rerun_needed = False
        _executor = None

    if executor is not None:
        executor.shutdown(wait=False, cancel_futures=True)
        logger.info(
            "geocode_post_commit_worker executor shutdown (jobs processing recoverable via lease)"
        )


def _submit_drain_run(batch_limit: int) -> Future:
    """Envía una corrida de drain al executor (una sola activa por ``_drain_scheduled``)."""

    def _run() -> None:
        global _drain_scheduled, _drain_rerun_needed
        max_rounds = max(1, int(os.getenv("GEO_POST_COMMIT_DRAIN_MAX_ROUNDS", "500")))
        rounds = 0
        try:
            assert _app is not None
            with _app.app_context():
                try:
                    while True:
                        rounds += 1
                        if rounds > max_rounds:
                            pending = count_pending_geocode_post_commit_jobs()
                            if pending > 0:
                                with _drain_lock:
                                    _drain_rerun_needed = True
                                logger.warning(
                                    "GEO_DRAIN_MAX_ROUNDS reached rounds=%s pending=%s reschedule=true",
                                    max_rounds,
                                    pending,
                                )
                            else:
                                logger.warning(
                                    "GEO_DRAIN_MAX_ROUNDS reached rounds=%s pending=0",
                                    max_rounds,
                                )
                            break
                        summary = process_geocode_post_commit_jobs(limit=batch_limit)
                        if summary.get("claimed", 0) > 0:
                            continue
                        with _drain_lock:
                            if _drain_rerun_needed:
                                _drain_rerun_needed = False
                                logger.info("GEO_DRAIN_RERUN reason=coalesced_schedule")
                                continue
                        break
                finally:
                    db.session.remove()
        except Exception:
            logger.exception("geocode_post_commit_worker drain failed")
        finally:
            reschedule = False
            with _drain_lock:
                _drain_scheduled = False
                if _drain_rerun_needed:
                    _drain_rerun_needed = False
                    reschedule = True
            if reschedule:
                logger.info("GEO_DRAIN_RERUN reason=drain_exit_reschedule")
                schedule_geocode_post_commit_drain()

    assert _executor is not None
    future = _executor.submit(_run)
    future.add_done_callback(_on_drain_future_done)
    return future


def schedule_geocode_post_commit_drain(limit: Optional[int] = None) -> DrainScheduleOutcome:
    """
    Programa drenado de la cola en el executor controlado.

    Si ya hay un drain activo, marca ``_drain_rerun_needed`` para reprogramar al
    finalizar la corrida actual (GEO-PERF.2).

    Returns:
        ``scheduled`` si se lanzó una corrida nueva;
        ``coalesced`` si ya había drain activo y quedó marcado rerun;
        ``async_disabled`` o ``executor_unavailable`` si no se pudo programar;
        ``executor_submit_failed`` si la reserva del drain no pudo enviarse al executor.
    """
    global _drain_scheduled, _drain_rerun_needed

    if not geocode_post_commit_async_enabled():
        return "async_disabled"
    if _executor is None or _app is None:
        logger.warning(
            "GEO_DRAIN_NOT_SCHEDULED reason=executor_unavailable executor=%s app=%s",
            _executor is not None,
            _app is not None,
        )
        return "executor_unavailable"

    batch_limit = int(limit or os.getenv("GEO_POST_COMMIT_DRAIN_LIMIT", "50"))

    with _drain_lock:
        if _drain_scheduled:
            _drain_rerun_needed = True
            logger.info(
                "GEO_DRAIN_COALESCED reason=already_running rerun_needed=true"
            )
            return "coalesced"
        _drain_scheduled = True

    logger.info("GEO_DRAIN_SCHEDULED")
    try:
        _submit_drain_run(batch_limit)
    except Exception as exc:
        with _drain_lock:
            _drain_scheduled = False
        logger.error(
            "GEO_DRAIN_SUBMIT_FAILED error=%s",
            exc,
            exc_info=exc,
        )
        return "executor_submit_failed"
    return "scheduled"


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
