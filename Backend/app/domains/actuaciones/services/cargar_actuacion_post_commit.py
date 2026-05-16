"""
Post-commit operativos tras persistir datos de actuación que pueden habilitar
``REINSPECCION_NOTIFICACION`` (misma corrida canónica que CLI y POST sync).

Se usa después de:
- alta/edición por **Cargar actuación** (grid);
- cierre exitoso de **Completar trabajo** (actas del día en actuación vinculada a ruta).

No duplica reglas: delega en ``sync_iniciadores_reinspeccion_notificacion``.
"""

from __future__ import annotations

import logging

from app.domains.actuaciones.services.notificacion_iniciador_service import (
    sync_iniciadores_reinspeccion_notificacion,
)

logger = logging.getLogger(__name__)


def ejecutar_sync_reinspeccion_notificacion_post_cargar_actuacion_canal() -> None:
    """
    Materializa iniciadores `REINSPECCION_NOTIFICACION` si corresponde (sync global idempotente).

    Qué hace: invoca `sync_iniciadores_reinspeccion_notificacion()`.

    Errores: no relanza; si el sync falla, la transacción principal ya hizo commit — se deja traza en log.
    """
    try:
        sync_iniciadores_reinspeccion_notificacion()
    except Exception:
        logger.exception(
            "Falló sync_iniciadores_reinspeccion_notificacion tras persistir actuación "
            "(la operación principal sí se guardó; reintentar sync manual o cron)."
        )
