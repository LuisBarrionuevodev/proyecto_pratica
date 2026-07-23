"""Preserva geocode existente en ediciones textuales de domicilio (canales documentales)."""

from __future__ import annotations

from typing import Any

from app.database import db
from app.models import Domicilio, DomicilioGeocode
from app.domains.geolocalizacion.geocoding.repos.domicilio_geocode_repo import (
    ensure_geocode_row,
)
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    compute_addr_hash,
)

_GEO_SNAPSHOT_FIELDS = (
    "lat",
    "lng",
    "geo_status",
    "provider",
    "quality",
    "score",
    "error_msg",
    "raw_json",
    "addr_hash",
    "source",
    "checked_at",
)


def snapshot_domicilio_geocode(domicilio_id: int) -> dict[str, Any] | None:
    """
    Captura la fila ``domicilio_geocode`` antes de editar texto operativo.

    Retorna ``None`` si no hay geocode persistido con coordenadas o estado útil.
    """
    geo = (
        DomicilioGeocode.query.filter_by(domicilio_id=int(domicilio_id))
        .filter(DomicilioGeocode.deleted_at.is_(None))
        .first()
    )
    if geo is None:
        return None
    if geo.lat is None and geo.lng is None and geo.geo_status in (
        "PENDING",
        "NORM_PENDING",
        "GEO_PENDING",
        "NO_MATCH",
    ):
        return None
    return {field: getattr(geo, field) for field in _GEO_SNAPSHOT_FIELDS}


def restaurar_domicilio_geocode_desde_snapshot(
    domicilio_id: int,
    snapshot: dict[str, Any] | None,
) -> None:
    """Restaura campos de geocode desde snapshot (sin commit)."""
    if not snapshot:
        return
    geo = ensure_geocode_row(int(domicilio_id))
    for field in _GEO_SNAPSHOT_FIELDS:
        setattr(geo, field, snapshot.get(field))
    db.session.add(geo)


def preservar_geocode_existente_al_editar_domicilio(
    domicilio_id: int,
    snapshot: dict[str, Any] | None,
) -> None:
    """
    Restaura geocode previo tras edición textual en la misma fila de domicilio.

    Usado en Completar Trabajo / Actuaciones: el texto puede cambiar sin invalidar lat/lng.
    Sella ``addr_hash`` al texto actual y marca ``source=MANUAL`` para evitar refresh accidental.
    """
    restaurar_domicilio_geocode_desde_snapshot(domicilio_id, snapshot)
    dom = db.session.get(Domicilio, int(domicilio_id))
    if dom is None:
        return
    geo = ensure_geocode_row(int(domicilio_id))
    geo.addr_hash = compute_addr_hash(dom)
    if geo.lat is not None and geo.lng is not None:
        geo.geo_status = (snapshot or {}).get("geo_status") or geo.geo_status or "OK"
    geo.source = "MANUAL"
    db.session.add(geo)
