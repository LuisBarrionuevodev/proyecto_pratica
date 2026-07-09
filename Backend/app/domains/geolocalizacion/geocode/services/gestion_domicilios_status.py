"""
Estado operativo y geo_chip para Gestión Domicilios (PR6C.3).

Reglas puras SQL/Python sin ``match_calle``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, case, or_

from app.models import DomicilioGeocode

if TYPE_CHECKING:
    from app.models import Domicilio

StatusOperativoRow = str

GEO_SCORE_DUDOSO = 0.85

STATUS_LABELS: dict[str, str] = {
    "sin_punto": "Sin punto",
    "punto_dudoso": "Punto dudoso",
    "error": "Error",
    "manual": "Manual",
    "geolocalizado": "Geolocalizado",
}


def requiere_accion(status: StatusOperativoRow) -> bool:
    """True si el domicilio entra en la cola operativa de geolocalización."""
    return status in {"sin_punto", "punto_dudoso", "error"}


def _geo_has_coords(geo: DomicilioGeocode | None) -> bool:
    if geo is None or geo.deleted_at is not None:
        return False
    return geo.lat is not None and geo.lng is not None


def resolve_status_operativo(
    dom: Domicilio | None,
    geo: DomicilioGeocode | None,
) -> StatusOperativoRow:
    """
    Resuelve estado operativo simple para operador.

    Prioridad: error → manual → sin_punto → punto_dudoso → geolocalizado.
    """
    _ = dom
    if geo is None or geo.deleted_at is not None:
        return "sin_punto"

    geo_status = (geo.geo_status or "PENDING").strip().upper()
    source = (geo.source or "").strip().upper()
    has_coords = _geo_has_coords(geo)

    if geo_status in {"ERROR", "NO_MATCH"}:
        return "error"

    if source == "MANUAL" and has_coords:
        return "manual"

    if not has_coords:
        return "sin_punto"

    if geo_status == "REVIEW":
        return "punto_dudoso"

    score = geo.score
    quality = (geo.quality or "").strip().lower()
    if score is not None and float(score) < GEO_SCORE_DUDOSO:
        return "punto_dudoso"
    if quality and quality != "building":
        return "punto_dudoso"

    if geo_status == "OK" and source != "MANUAL":
        return "geolocalizado"

    if geo_status in {"PENDING", "NORM_PENDING", "GEO_PENDING"}:
        return "sin_punto"

    return "punto_dudoso"


def resolve_geo_chip(geo: DomicilioGeocode | None) -> tuple[str, bool]:
    """Retorna (geo_chip, has_coordinates)."""
    has = _geo_has_coords(geo)
    return ("EN_MAPA" if has else "SIN_COORDS", has)


def status_operativo_sql_case():
    """
    Expresión SQLAlchemy CASE para filtrar/agrupar por ``status_operativo``.

    Debe mantener la misma prioridad que ``resolve_status_operativo``.
    """
    has_coords = and_(
        DomicilioGeocode.domicilio_id.isnot(None),
        DomicilioGeocode.deleted_at.is_(None),
        DomicilioGeocode.lat.isnot(None),
        DomicilioGeocode.lng.isnot(None),
    )
    geo_active = and_(
        DomicilioGeocode.domicilio_id.isnot(None),
        DomicilioGeocode.deleted_at.is_(None),
    )
    is_error = and_(
        geo_active,
        DomicilioGeocode.geo_status.in_(["ERROR", "NO_MATCH"]),
    )
    is_manual = and_(has_coords, DomicilioGeocode.source == "MANUAL")
    is_sin_punto = or_(
        DomicilioGeocode.domicilio_id.is_(None),
        DomicilioGeocode.deleted_at.isnot(None),
        DomicilioGeocode.lat.is_(None),
        DomicilioGeocode.lng.is_(None),
    )
    is_punto_dudoso = and_(
        has_coords,
        or_(
            DomicilioGeocode.geo_status == "REVIEW",
            and_(DomicilioGeocode.score.isnot(None), DomicilioGeocode.score < GEO_SCORE_DUDOSO),
            and_(
                DomicilioGeocode.quality.isnot(None),
                DomicilioGeocode.quality != "building",
            ),
            and_(
                DomicilioGeocode.geo_status.in_(["PENDING", "NORM_PENDING", "GEO_PENDING"]),
            ),
        ),
    )
    is_geolocalizado = and_(
        has_coords,
        DomicilioGeocode.geo_status == "OK",
        or_(DomicilioGeocode.source.is_(None), DomicilioGeocode.source != "MANUAL"),
        or_(DomicilioGeocode.score.is_(None), DomicilioGeocode.score >= GEO_SCORE_DUDOSO),
        or_(
            DomicilioGeocode.quality.is_(None),
            DomicilioGeocode.quality == "building",
        ),
    )

    return case(
        (is_error, "error"),
        (is_manual, "manual"),
        (is_sin_punto, "sin_punto"),
        (is_geolocalizado, "geolocalizado"),
        (is_punto_dudoso, "punto_dudoso"),
        else_="punto_dudoso",
    )
