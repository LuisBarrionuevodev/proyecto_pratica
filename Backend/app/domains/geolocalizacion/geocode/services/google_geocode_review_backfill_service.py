"""
GEO-REVIEW.1.1 — backfill de ``geo_status`` para resultados Google históricos.

Promueve ``GEO_PENDING`` → ``OK`` cuando ya existen coordenadas válidas,
sin volver a llamar a Google ni recalcular lat/lng.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Query

from app.database import db
from app.models import Domicilio, DomicilioGeocode


@dataclass
class GoogleGeocodeReviewBackfillSummary:
    """Resumen de corrida del backfill GEO-REVIEW.1.1."""

    mode: str
    candidatos: int = 0
    actualizados: int = 0
    omitidos: int = 0
    errores: int = 0
    sin_distrito: int = 0
    error_details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el resumen para logging o salida CLI."""
        return {
            "mode": self.mode,
            "candidatos": self.candidatos,
            "actualizados": self.actualizados,
            "omitidos": self.omitidos,
            "errores": self.errores,
            "sin_distrito": self.sin_distrito,
            "error_details": list(self.error_details),
        }


def _candidatos_google_geo_pending_con_coords_query(
    *,
    domicilio_id: Optional[int] = None,
) -> Query:
    """
    Candidatos elegibles: Google + GEO_PENDING + coords, excluyendo MANUAL.

    No incluye NO_MATCH, ERROR ni filas sin coordenadas.
    """
    query = (
        db.session.query(
            DomicilioGeocode.domicilio_id,
            Domicilio.distrito_id,
        )
        .join(Domicilio, Domicilio.id == DomicilioGeocode.domicilio_id)
        .filter(
            Domicilio.deleted_at.is_(None),
            DomicilioGeocode.deleted_at.is_(None),
            DomicilioGeocode.provider == "google",
            DomicilioGeocode.geo_status == "GEO_PENDING",
            DomicilioGeocode.lat.isnot(None),
            DomicilioGeocode.lng.isnot(None),
            or_(
                DomicilioGeocode.source.is_(None),
                DomicilioGeocode.source != "MANUAL",
            ),
        )
        .order_by(DomicilioGeocode.domicilio_id.asc())
    )
    if domicilio_id is not None:
        query = query.filter(DomicilioGeocode.domicilio_id == int(domicilio_id))
    return query


def count_google_geo_pending_con_coords(*, domicilio_id: Optional[int] = None) -> int:
    """Cuenta filas elegibles para el backfill."""
    return int(
        _candidatos_google_geo_pending_con_coords_query(domicilio_id=domicilio_id).count()
    )


def _fetch_candidatos(
    *,
    limit: Optional[int] = None,
    domicilio_id: Optional[int] = None,
) -> List[Tuple[int, Optional[int]]]:
    """Obtiene candidatos como ``(domicilio_id, distrito_id)``."""
    query = _candidatos_google_geo_pending_con_coords_query(domicilio_id=domicilio_id)
    if limit is not None:
        query = query.limit(int(limit))
    return [(int(row[0]), row[1]) for row in query.all()]


def run_google_geocode_review_status_backfill(
    *,
    apply: bool = False,
    limit: Optional[int] = None,
    domicilio_id: Optional[int] = None,
    batch_size: int = 100,
) -> GoogleGeocodeReviewBackfillSummary:
    """
    Promueve ``GEO_PENDING`` → ``OK`` en resultados Google con coordenadas.

    Idempotente: segunda corrida con mismos datos devuelve ``candidatos=0``.
    No llama APIs externas ni modifica lat/lng/quality/score.

    Args:
        apply: si True persiste; si False solo reporta (dry-run).
        limit: máximo de filas a procesar.
        domicilio_id: limitar a un domicilio.
        batch_size: commits por lote en modo apply.

    Returns:
        Resumen con candidatos, actualizados, omitidos y errores.
    """
    summary = GoogleGeocodeReviewBackfillSummary(
        mode="apply" if apply else "dry_run",
    )
    candidates = _fetch_candidatos(limit=limit, domicilio_id=domicilio_id)
    summary.candidatos = len(candidates)

    if not candidates:
        return summary

    if not apply:
        summary.actualizados = summary.candidatos
        summary.sin_distrito = sum(1 for _, distrito_id in candidates if distrito_id is None)
        return summary

    pending_commits = 0
    batch_size = max(1, int(batch_size))

    for dom_id, distrito_id in candidates:
        savepoint = db.session.begin_nested()
        try:
            geo = db.session.get(DomicilioGeocode, int(dom_id))
            if geo is None or geo.deleted_at is not None:
                summary.omitidos += 1
                savepoint.rollback()
                continue
            if str(geo.provider or "").lower() != "google":
                summary.omitidos += 1
                savepoint.rollback()
                continue
            if str(geo.geo_status or "") != "GEO_PENDING":
                summary.omitidos += 1
                savepoint.rollback()
                continue
            if geo.lat is None or geo.lng is None:
                summary.omitidos += 1
                savepoint.rollback()
                continue
            if str(geo.source or "").upper() == "MANUAL":
                summary.omitidos += 1
                savepoint.rollback()
                continue

            geo.geo_status = "OK"
            db.session.add(geo)
            savepoint.commit()
            summary.actualizados += 1
            pending_commits += 1
            if distrito_id is None:
                summary.sin_distrito += 1
            if pending_commits >= batch_size:
                db.session.commit()
                pending_commits = 0
        except Exception as exc:  # noqa: BLE001
            savepoint.rollback()
            summary.errores += 1
            summary.error_details.append(
                {"domicilio_id": int(dom_id), "error": str(exc)[:500]},
            )

    if pending_commits > 0:
        db.session.commit()

    return summary
