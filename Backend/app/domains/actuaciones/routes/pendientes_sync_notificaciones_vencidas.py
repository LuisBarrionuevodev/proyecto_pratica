"""
POST: ejecuta el mismo pipeline que el CLI `sync-notificaciones-vencidas` (Fase C).
"""

from __future__ import annotations

import logging

from flask import jsonify

from app.domains.actuaciones.pipelines.sync_notificaciones_vencidas import (
    run_sync_notificaciones_vencidas,
)
from app.security.rate_limiter import limit_sync_notificaciones_vencidas, limiter

from . import actuacion

logger = logging.getLogger(__name__)


@actuacion.post("/pendientes/sync-notificaciones-vencidas")
@limiter.limit(limit_sync_notificaciones_vencidas)
def post_pendientes_sync_notificaciones_vencidas():
    """
    Materializa iniciadores `REINSPECCION_NOTIFICACION` por notificaciones vencidas.

    Qué hace: invoca `run_sync_notificaciones_vencidas()` (misma lógica que CLI / scheduler).

    Parámetros: ninguno (body ignorado).

    Retorno:
        200 JSON con métricas: `status`, `created`, `eligible_notificaciones`,
        `skipped_already_blocking`, `collisions_idempotent`, `elapsed_ms`, `started_at`.

    Errores:
        401 sin JWT válido (guard global).
        429 rate limit.
        500 si falla la corrida (sin stacktrace al cliente).
    """
    try:
        metrics = run_sync_notificaciones_vencidas()
        return jsonify(metrics), 200
    except Exception:
        logger.exception("post_pendientes_sync_notificaciones_vencidas")
        return jsonify({"detail": "No se pudo completar la sincronización."}), 500
