from __future__ import annotations

from flask import jsonify

from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    list_reinspeccion_notificacion_operativas,
    materializacion_notificacion_vencida_on_read_enabled,
    sync_iniciadores_reinspeccion_notificacion,
)

from . import actuacion


@actuacion.get("/pendientes-notificacion")
def get_pendientes_notificacion():
    """
    Lista operativa de reinspecciones por notificación vencida.

    Fase C: no ejecuta materialización salvo `SYNC_NOTIFICACIONES_VENCIDAS_ON_READ=1` (transitorio).
    En producción, el sync debe correr vía CLI / scheduler.
    """
    if materializacion_notificacion_vencida_on_read_enabled():
        sync_iniciadores_reinspeccion_notificacion()
    acts = list_reinspeccion_notificacion_operativas()
    return jsonify([actuacion_to_grid_row(a) for a in acts]), 200

