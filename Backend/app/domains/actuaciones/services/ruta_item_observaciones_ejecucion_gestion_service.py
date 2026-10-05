"""Observaciones de ejecución (RutaItem) editables desde Gestión de Actuaciones."""

from __future__ import annotations

from typing import Any

from app.database import db
from app.domains.media.utils.ruta_item_resolver import resolve_ruta_item_id_for_actuacion
from app.models import RutaItem

_OBSERVACIONES_PAYLOAD_KEY = "observaciones_ejecucion"


def extraer_observaciones_ejecucion_gestion(payload: dict[str, Any]) -> dict[str, Any]:
    """Extrae y elimina del payload canónico ``observaciones_ejecucion``."""
    out: dict[str, Any] = {}
    if _OBSERVACIONES_PAYLOAD_KEY in payload:
        out[_OBSERVACIONES_PAYLOAD_KEY] = payload.pop(_OBSERVACIONES_PAYLOAD_KEY)
    return out


def validar_y_aplicar_observaciones_ejecucion_gestion_put(
    actuacion_id: int,
    fragmento: dict[str, Any],
) -> None:
    """
    Persiste observaciones de la visita en el ``RutaItem`` vinculado a la actuación.

    Parámetros:
        actuacion_id: actuación en edición.
        fragmento: subconjunto extraído del PUT (solo si el cliente envió la clave).

    Errores:
        ValueError: si se envía el campo pero no hay ítem de ruta operativo vinculado.
    """
    if not fragmento or _OBSERVACIONES_PAYLOAD_KEY not in fragmento:
        return

    item_id = resolve_ruta_item_id_for_actuacion(int(actuacion_id))
    if item_id is None:
        raise ValueError(
            "No hay ítem de ruta vinculado para guardar observaciones de la visita."
        )

    item = db.session.get(RutaItem, int(item_id))
    if item is None or item.deleted_at is not None:
        raise ValueError(
            "No hay ítem de ruta vinculado para guardar observaciones de la visita."
        )

    raw = fragmento.get(_OBSERVACIONES_PAYLOAD_KEY)
    if raw is None:
        item.observaciones_ejecucion = None
    else:
        s = str(raw).strip()
        item.observaciones_ejecucion = s or None
    db.session.add(item)
