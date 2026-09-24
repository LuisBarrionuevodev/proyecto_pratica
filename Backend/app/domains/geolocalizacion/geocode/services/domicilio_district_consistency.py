from __future__ import annotations

import logging
from typing import Optional

from app.models import Domicilio

logger = logging.getLogger(__name__)


def log_barrio_distrito_consistency(
    *,
    domicilio: Domicilio,
    source: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> None:
    """
    Registra advertencia si barrio y distrito del domicilio quedaron inconsistentes.

    Args:
        domicilio: instancia de domicilio ya actualizada en sesión.
        source: origen de asignación (AUTO/MANUAL/REVERSE/BACKFILL).
        lat: latitud usada para resolver distrito (opcional).
        lng: longitud usada para resolver distrito (opcional).
    """
    if not domicilio:
        return
    if domicilio.barrio_id is None or domicilio.distrito_id is None:
        return

    barrio = getattr(domicilio, "barrio", None)
    barrio_distrito_id = getattr(barrio, "distrito_id", None) if barrio else None
    if barrio_distrito_id is None:
        return

    if int(barrio_distrito_id) != int(domicilio.distrito_id):
        logger.warning(
            "district_consistency_warning %s",
            {
                "domicilio_id": int(domicilio.id),
                "barrio_id": int(domicilio.barrio_id),
                "barrio_distrito_id": int(barrio_distrito_id),
                "domicilio_distrito_id": int(domicilio.distrito_id),
                "source": source,
                "lat": lat,
                "lng": lng,
            },
        )
