from __future__ import annotations

import logging
from typing import Optional


_LOGGER = logging.getLogger(__name__)


def log_district_event(
    *,
    event: str,
    domicilio_id: int,
    lat: Optional[float],
    lng: Optional[float],
    source: str,
    geo_status: str,
    distrito_id: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """
    Registra un evento operativo de asignacion de distrito con payload uniforme.

    Args:
        event: tipo de evento (`district_assigned`, `district_no_match`, `district_error`).
        domicilio_id: id del domicilio.
        lat: latitud usada para resolver.
        lng: longitud usada para resolver.
        source: origen del flujo (`AUTO`, `MANUAL`, `REVERSE`, `BACKFILL`).
        geo_status: estado de geocoding asociado.
        distrito_id: distrito asignado si aplica.
        error: detalle de error tecnico en caso de fallo.
    """
    payload = {
        "event": event,
        "domicilio_id": domicilio_id,
        "lat": lat,
        "lng": lng,
        "source": source,
        "geo_status": geo_status,
        "distrito_id": distrito_id,
    }
    if error:
        payload["error"] = error

    if event == "district_error":
        _LOGGER.warning("district_error %s", payload)
        return
    _LOGGER.info("%s %s", event, payload)
