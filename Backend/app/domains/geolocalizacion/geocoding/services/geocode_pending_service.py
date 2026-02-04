from __future__ import annotations

from typing import Dict, List

from sqlalchemy import and_, or_

from app.models import Domicilio, DomicilioGeocode
from app.domains.geolocalizacion.geocoding.services.geocode_service import (
    geocode_domicilio,
)


def _base_pending_query():
    return (
        Domicilio.query.filter(Domicilio.deleted_at.is_(None))
        .filter(Domicilio.calle_norm_status == "OK")
        .filter(
            or_(
                Domicilio.numero_tipo != "ESQUINA",
                and_(
                    Domicilio.numero_tipo == "ESQUINA",
                    Domicilio.esquina_norm_status == "OK",
                ),
            )
        )
    )


def list_pendientes_geocode(limit: int = 200) -> List[Domicilio]:
    """
    Lista domicilios normalizados que aún no tienen geocode OK.

    Args:
        limit: cantidad máxima.

    Returns:
        Lista de domicilios candidatos a geocodificar.
    """
    query = _base_pending_query().outerjoin(
        DomicilioGeocode, Domicilio.id == DomicilioGeocode.domicilio_id
    ).filter(or_(DomicilioGeocode.domicilio_id.is_(None), DomicilioGeocode.geo_status != "OK"))
    return query.order_by(Domicilio.id.desc()).limit(limit).all()


def geocode_pendientes(limit: int = 200) -> Dict[str, int]:
    """
    Geocodifica domicilios pendientes en batch.

    Args:
        limit: cantidad máxima.

    Returns:
        Resumen de resultados por status.
    """
    items = list_pendientes_geocode(limit=limit)
    summary = {
        "processed": 0,
        "ok_count": 0,
        "review_count": 0,
        "no_match_count": 0,
        "error_count": 0,
    }
    for dom in items:
        result = geocode_domicilio(dom.id)
        summary["processed"] += 1
        status = result.get("geo_status") or result.get("status")
        if status == "OK":
            summary["ok_count"] += 1
        elif status == "REVIEW":
            summary["review_count"] += 1
        elif status == "NO_MATCH":
            summary["no_match_count"] += 1
        elif status == "ERROR":
            summary["error_count"] += 1
    return summary
