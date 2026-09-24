"""
GEO-PERF.1 / 1.1 — cola durable y procesamiento de geocode post-commit.

Encola ``pipeline_post_commit`` fuera del request HTTP de grid commit.
Claim atómico: ``SELECT ... FOR UPDATE SKIP LOCKED`` + ``UPDATE WHERE status='pending'``.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Set

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import db
from app.domains.geolocalizacion.geocode.services.pipeline_service import pipeline_post_commit
from app.domains.geolocalizacion.geocoding.repos.domicilio_geocode_repo import ensure_geocode_row
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    compute_addr_hash,
    is_ready_for_geocode,
)
from app.domains.geolocalizacion.geocoding.services.geocode_service import (
    get_geocoder_provider,
)
from app.domains.geolocalizacion.geocoding.services.google_geocode_adapter import (
    google_can_attempt,
)
from app.models import Domicilio, DomicilioGeocode, GeocodePostCommitJob

logger = logging.getLogger(__name__)


def _max_attempts() -> int:
    return int(os.getenv("GEO_POST_COMMIT_MAX_ATTEMPTS", "3"))


def _processing_lease_seconds() -> int:
    return int(os.getenv("GEO_POST_COMMIT_PROCESSING_LEASE_SEC", "300"))


def _utcnow() -> datetime:
    return datetime.utcnow()


def domicilio_necesita_geocode_post_commit(domicilio_id: int) -> bool:
    """
    True si el domicilio no tiene geocode OK cacheado y conviene encolar pipeline.

    Preserva FIX.10A: geo OK + coords → no re-geocodificar.
    """
    dom = db.session.get(Domicilio, int(domicilio_id))
    if not dom or dom.deleted_at is not None:
        return False

    geo = (
        DomicilioGeocode.query.filter(
            DomicilioGeocode.domicilio_id == int(domicilio_id),
            DomicilioGeocode.deleted_at.is_(None),
        )
        .first()
    )
    if (
        geo is not None
        and str(geo.geo_status or "") == "OK"
        and geo.lat is not None
        and geo.lng is not None
    ):
        return False
    if geo is not None and str(geo.source or "") in {"MANUAL", "REVERSE"} and not geo.addr_hash:
        return False
    return True


def prepare_geocode_state_after_commit(domicilio_id: int) -> None:
    """
    Marca estado geo pendiente en DB sin llamar al proveedor externo.

    Deja ``NORM_PENDING`` o ``GEO_PENDING`` según normalización actual.
    """
    dom = db.session.get(Domicilio, int(domicilio_id))
    if not dom or dom.deleted_at is not None:
        return

    geo = ensure_geocode_row(int(domicilio_id))
    if (
        str(geo.geo_status or "") == "OK"
        and geo.lat is not None
        and geo.lng is not None
    ):
        geo.addr_hash = compute_addr_hash(dom)
        db.session.add(geo)
        db.session.commit()
        return

    provider = get_geocoder_provider()
    if provider == "google" and google_can_attempt(dom):
        geo.geo_status = "GEO_PENDING"
    elif not is_ready_for_geocode(dom):
        geo.geo_status = "NORM_PENDING"
    else:
        geo.geo_status = "GEO_PENDING"
    # No sellar addr_hash aquí: on_domicilio_changed usa el hash para detectar cambios
    # y decidir si geocodificar. Si lo seteamos antes del worker, salta con hash_unchanged.
    if not geo.source or str(geo.source) not in {"MANUAL", "REVERSE"}:
        geo.source = "AUTO"
    db.session.add(geo)
    db.session.commit()


def reclaim_stale_processing_jobs() -> int:
    """
    Reclama jobs ``processing`` cuyo lease expiró (worker muerto / reinicio).

    Returns:
        Cantidad de jobs devueltos a ``pending``.
    """
    cutoff = _utcnow() - timedelta(seconds=_processing_lease_seconds())
    stale = (
        GeocodePostCommitJob.query.filter(
            GeocodePostCommitJob.status == "processing",
            GeocodePostCommitJob.processing_started_at.isnot(None),
            GeocodePostCommitJob.processing_started_at < cutoff,
        )
        .all()
    )
    if not stale:
        return 0

    now = _utcnow()
    for job in stale:
        job.status = "pending"
        job.processing_started_at = None
        job.claimed_addr_hash = None
        job.updated_at = now
        db.session.add(job)
        logger.warning(
            "geocode_post_commit_job reclaimed job_id=%s domicilio_id=%s attempt=%s",
            job.id,
            job.domicilio_id,
            job.attempts,
        )
    db.session.commit()
    return len(stale)


def _claim_one_job_atomic() -> Optional[int]:
    """
    Toma un job ``pending`` de forma atómica (multiproceso seguro).

    Returns:
        job_id reclamado o None.
    """
    now = _utcnow()
    try:
        row = db.session.execute(
            text(
                """
                SELECT id, domicilio_id
                FROM geocode_post_commit_job
                WHERE status = 'pending'
                ORDER BY id ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """
            )
        ).fetchone()
        if row is None:
            db.session.rollback()
            return None

        job_id = int(row[0])
        domicilio_id = int(row[1])
        dom = db.session.get(Domicilio, domicilio_id)
        claimed_hash = compute_addr_hash(dom) if dom else None

        updated = db.session.execute(
            text(
                """
                UPDATE geocode_post_commit_job
                SET status = 'processing',
                    processing_started_at = :now,
                    updated_at = :now,
                    claimed_addr_hash = :claimed_hash
                WHERE id = :job_id AND status = 'pending'
                """
            ),
            {"job_id": job_id, "now": now, "claimed_hash": claimed_hash},
        )
        if int(updated.rowcount or 0) != 1:
            db.session.rollback()
            return None

        db.session.commit()
        return job_id
    except SQLAlchemyError:
        db.session.rollback()
        raise


def _geo_outcome_snapshot(domicilio_id: int) -> Dict[str, Optional[str]]:
    """Lee geo_status y provider efectivos tras ejecutar el pipeline."""
    geo = (
        DomicilioGeocode.query.filter(
            DomicilioGeocode.domicilio_id == int(domicilio_id),
            DomicilioGeocode.deleted_at.is_(None),
        )
        .first()
    )
    if geo is None:
        return {"geo_status": None, "provider": None}
    return {
        "geo_status": str(geo.geo_status) if geo.geo_status is not None else None,
        "provider": str(geo.provider) if geo.provider is not None else None,
    }


def _address_changed_since_claim(job: GeocodePostCommitJob) -> bool:
    """True si el domicilio cambió desde el claim (addr_hash distinto)."""
    if not job.claimed_addr_hash:
        return False
    dom = db.session.get(Domicilio, int(job.domicilio_id))
    if not dom:
        return False
    return compute_addr_hash(dom) != str(job.claimed_addr_hash)


def _persist_job_outcome(
    job_id: int,
    *,
    status: str,
    attempts: Optional[int] = None,
    last_error: Optional[str] = None,
    clear_processing: bool = True,
) -> None:
    """Persiste estado final del job releyendo la fila (evita StaleDataError)."""
    job = db.session.get(GeocodePostCommitJob, int(job_id))
    if job is None or job.status != "processing":
        return
    job.status = status
    job.updated_at = _utcnow()
    if attempts is not None:
        job.attempts = int(attempts)
    if last_error is not None:
        job.last_error = last_error
    elif status == "done":
        job.last_error = None
    if clear_processing:
        job.processing_started_at = None
        job.claimed_addr_hash = None
    db.session.add(job)
    db.session.commit()


def _process_claimed_job(job_id: int, summary: Dict[str, Any]) -> None:
    """
    Ejecuta pipeline para un job ya reclamado.

    ``done`` significa que el pipeline terminó sin error técnico; el estado geográfico
    real vive en ``DomicilioGeocode.geo_status`` (puede ser OK, NORM_PENDING, etc.).
    """
    job = db.session.get(GeocodePostCommitJob, int(job_id))
    if job is None or job.status != "processing":
        return

    domicilio_id = int(job.domicilio_id)
    attempts_before = int(job.attempts or 0)
    t0 = time.perf_counter()
    final_status = "done"
    geo_outcome: Dict[str, Optional[str]] = {"geo_status": None, "provider": None}

    try:
        if not domicilio_necesita_geocode_post_commit(domicilio_id):
            _persist_job_outcome(job_id, status="done")
            geo_outcome = _geo_outcome_snapshot(domicilio_id)
            summary["skipped"] += 1
            final_status = "done"
        else:
            pipeline_post_commit(domicilio_id)
            job = db.session.get(GeocodePostCommitJob, int(job_id))
            if job is None or job.status != "processing":
                return
            geo_outcome = _geo_outcome_snapshot(domicilio_id)
            if _address_changed_since_claim(job):
                _persist_job_outcome(job_id, status="pending")
                final_status = "pending"
                summary["requeued"] = int(summary.get("requeued", 0)) + 1
                logger.info(
                    "geocode_post_commit_job requeued job_id=%s domicilio_id=%s reason=address_changed",
                    job_id,
                    domicilio_id,
                )
            else:
                _persist_job_outcome(job_id, status="done")
                final_status = "done"
                summary["done"] += 1
    except Exception as exc:  # noqa: BLE001 - job aislado
        db.session.rollback()
        new_attempts = attempts_before + 1
        if new_attempts >= _max_attempts():
            _persist_job_outcome(
                job_id,
                status="failed",
                attempts=new_attempts,
                last_error=str(exc)[:500],
            )
            final_status = "failed"
            summary["failed"] += 1
        else:
            _persist_job_outcome(
                job_id,
                status="pending",
                attempts=new_attempts,
                last_error=str(exc)[:500],
            )
            final_status = "pending"
        logger.warning(
            "geocode_post_commit_job error job_id=%s domicilio_id=%s attempt=%s status=%s: %s",
            job_id,
            domicilio_id,
            new_attempts,
            final_status,
            exc,
        )
    finally:
        duration_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        job = db.session.get(GeocodePostCommitJob, int(job_id))
        attempt_log = int(job.attempts or 0) if job else attempts_before
        error_log = (job.last_error or "")[:120] if job else ""
        if not geo_outcome.get("geo_status"):
            geo_outcome = _geo_outcome_snapshot(domicilio_id)
        logger.info(
            "GEO_JOB_FINISHED job_id=%s domicilio_id=%s job_status=%s "
            "geo_status=%s provider=%s attempt=%s duration_ms=%s error=%s",
            job_id,
            domicilio_id,
            final_status,
            geo_outcome.get("geo_status"),
            geo_outcome.get("provider"),
            attempt_log,
            duration_ms,
            error_log,
        )
        summary["processed"] += 1


def enqueue_geocode_post_commit(domicilio_ids: Iterable[int]) -> List[int]:
    """
    Encola domicilios únicos para ``pipeline_post_commit`` asíncrono.

    Args:
        domicilio_ids: ids afectados por commit-batch (deduplicados).

    Returns:
        Lista de domicilio_id realmente encolados.
    """
    unique_ids: List[int] = []
    seen: Set[int] = set()
    for raw_id in domicilio_ids:
        domicilio_id = int(raw_id)
        if domicilio_id in seen:
            continue
        seen.add(domicilio_id)
        if not domicilio_necesita_geocode_post_commit(domicilio_id):
            continue
        prepare_geocode_state_after_commit(domicilio_id)
        unique_ids.append(domicilio_id)

    if not unique_ids:
        return []

    active = (
        GeocodePostCommitJob.query.filter(
            GeocodePostCommitJob.domicilio_id.in_(unique_ids),
            GeocodePostCommitJob.status.in_(("pending", "processing")),
        )
        .all()
    )
    active_ids = {int(row.domicilio_id) for row in active}

    enqueued: List[int] = []
    new_jobs: List[GeocodePostCommitJob] = []
    now = _utcnow()
    for domicilio_id in unique_ids:
        if domicilio_id in active_ids:
            continue
        job = GeocodePostCommitJob(
            domicilio_id=int(domicilio_id),
            status="pending",
            attempts=0,
            created_at=now,
            updated_at=now,
        )
        db.session.add(job)
        new_jobs.append(job)
        enqueued.append(int(domicilio_id))

    if enqueued:
        db.session.flush()
        for job in new_jobs:
            logger.info(
                "GEO_JOB_ENQUEUED domicilio_id=%s job_id=%s",
                job.domicilio_id,
                job.id,
            )
        db.session.commit()
    return enqueued


def process_geocode_post_commit_jobs(limit: int = 50) -> Dict[str, Any]:
    """
    Procesa trabajos pendientes llamando al pipeline existente.

    Claim atómico por job; seguro con múltiples procesos Flask o CLI concurrente.
    """
    summary: Dict[str, Any] = {
        "claimed": 0,
        "processed": 0,
        "done": 0,
        "failed": 0,
        "skipped": 0,
        "requeued": 0,
        "reclaimed": 0,
    }

    summary["reclaimed"] = reclaim_stale_processing_jobs()

    for _ in range(int(limit)):
        job_id = _claim_one_job_atomic()
        if job_id is None:
            break
        summary["claimed"] += 1
        try:
            _process_claimed_job(job_id, summary)
        except Exception:
            db.session.rollback()
            raise
        finally:
            db.session.remove()

    return summary


def count_recoverable_geocode_post_commit_jobs() -> int:
    """Cuenta jobs pendientes o processing (incluye abandonados recuperables)."""
    return int(
        GeocodePostCommitJob.query.filter(
            GeocodePostCommitJob.status.in_(("pending", "processing"))
        ).count()
    )


def count_pending_geocode_post_commit_jobs() -> int:
    """Cuenta jobs en estado ``pending`` (sin incluir ``processing``)."""
    return int(
        GeocodePostCommitJob.query.filter(
            GeocodePostCommitJob.status == "pending"
        ).count()
    )
