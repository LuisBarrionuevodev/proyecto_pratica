"""
Confianza de geocode unificada entre proveedores (Geoapify vs Google).

Google no expone un score 0..1 como Geoapify; mapeamos ``location_type`` / precision
a un score de display para mapas y clasificación operativa.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models import DomicilioGeocode

GEOAPIFY_AUTO_OK_SCORE = 0.95
GEO_SCORE_DUDOSO = 0.85

GOOGLE_PRECISION_SCORE: dict[str, float] = {
    "ROOFTOP": 1.0,
    "INTERPOLATED": 0.92,
    "GEOMETRIC_CENTER": 0.90,
    "APPROXIMATE": 0.70,
}

# Metadata/display only (GEO-REVIEW.1); no usado para revisión manual.
GOOGLE_TRUSTED_PRECISIONS = frozenset(
    {"ROOFTOP", "INTERPOLATED", "GEOMETRIC_CENTER", "APPROXIMATE"}
)


def google_precision_to_display_score(precision: Optional[str]) -> Optional[float]:
    """
    Mapea precision Google a score 0..1 para UI/clasificación.

    No es el rank de Geoapify; es una equivalencia operativa documentada.
    """
    if not precision:
        return None
    return GOOGLE_PRECISION_SCORE.get(str(precision).upper())


def is_google_geolocalizado(geo: DomicilioGeocode | None) -> bool:
    """
    True si Google devolvió coords utilizables con ``geo_status=OK`` (GEO-REVIEW.1).

    No evalúa score, quality ni partial_match.
    """
    if geo is None or getattr(geo, "deleted_at", None) is not None:
        return False
    if str(geo.provider or "").strip().lower() != "google":
        return False
    if str(geo.geo_status or "").upper() != "OK":
        return False
    return geo.lat is not None and geo.lng is not None


def is_trusted_auto_geocode(geo: DomicilioGeocode | None) -> bool:
    """
    True si el punto AUTO tiene confianza suficiente para mapa operativo.

    Geoapify: ``quality == building`` y score >= umbral dudoso.
    Google (GEO-REVIEW.1): ``geo_status=OK`` + coords (sin filtro por precision/score).
    """
    if geo is None or getattr(geo, "deleted_at", None) is not None:
        return False
    if str(geo.geo_status or "").upper() != "OK":
        return False
    if str(geo.source or "").upper() == "MANUAL":
        return True

    provider = str(geo.provider or "").strip().lower()
    quality = str(geo.quality or "").strip()

    if provider == "google":
        return is_google_geolocalizado(geo)

    q_lower = quality.lower()
    if q_lower and q_lower != "building":
        return False
    score = geo.score
    if score is None:
        return q_lower == "building"
    try:
        return float(score) >= GEO_SCORE_DUDOSO
    except (TypeError, ValueError):
        return False
