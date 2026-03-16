from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.domains.geolocalizacion.geocode.services.distritos_service import (
    resolve_distrito_id,
)
from app.models import Domicilio, DomicilioGeocode


def run_distrito_backfill(*, limit: Optional[int] = None, force: bool = False) -> Dict[str, Any]:
    """
    Ejecuta backfill de distrito para domicilios geocodificados en estado OK.

    Reglas:
    - Solo domicilios no eliminados.
    - Solo geocode no eliminado, con status OK y lat/lng presentes.
    - En modo incremental (force=False), procesa solo domicilios sin distrito_id.
    - En modo force=True, recalcula todos los elegibles.

    Args:
        limit: máximo de registros a procesar.
        force: si True recalcula aunque el domicilio ya tenga distrito_id.

    Returns:
        Resumen de corrida con métricas de resultado.
    """
    summary: Dict[str, Any] = {
        "processed": 0,
        "assigned": 0,
        "updated": 0,
        "no_match": 0,
        "errors": 0,
        "skipped": 0,
        "force": force,
        "limit": limit,
    }

    query = (
        db.session.query(Domicilio, DomicilioGeocode)
        .join(
            DomicilioGeocode,
            Domicilio.id == DomicilioGeocode.domicilio_id,
        )
        .filter(
            Domicilio.deleted_at.is_(None),
            DomicilioGeocode.deleted_at.is_(None),
            DomicilioGeocode.geo_status == "OK",
            DomicilioGeocode.lat.isnot(None),
            DomicilioGeocode.lng.isnot(None),
        )
        .order_by(Domicilio.id.asc())
    )
    if not force:
        query = query.filter(Domicilio.distrito_id.is_(None))
    if limit is not None:
        query = query.limit(limit)

    rows = query.all()
    for domicilio, geo in rows:
        summary["processed"] += 1
        try:
            resolved_distrito_id = resolve_distrito_id(float(geo.lat), float(geo.lng))
        except Exception:
            summary["errors"] += 1
            continue

        previous_distrito_id = domicilio.distrito_id
        if resolved_distrito_id is None:
            summary["no_match"] += 1
            if force and previous_distrito_id is not None:
                domicilio.distrito_id = None
                db.session.add(domicilio)
                summary["updated"] += 1
            continue

        if previous_distrito_id is None:
            domicilio.distrito_id = resolved_distrito_id
            db.session.add(domicilio)
            summary["assigned"] += 1
            continue

        if int(previous_distrito_id) != int(resolved_distrito_id):
            domicilio.distrito_id = resolved_distrito_id
            db.session.add(domicilio)
            summary["updated"] += 1
            continue

        summary["skipped"] += 1

    db.session.commit()
    return summary

