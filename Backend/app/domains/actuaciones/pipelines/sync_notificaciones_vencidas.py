from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone

from app.domains.actuaciones.services.notificacion_iniciador_service import (
    sync_iniciadores_reinspeccion_notificacion,
)

logger = logging.getLogger(__name__)


def run_sync_notificaciones_vencidas() -> dict[str, int | float | str]:
    """
    Ejecuta el sync de iniciadores por notificaciones vencidas (camino canónico operativo, Fase C).

    Returns:
        Métricas operativas de la corrida.
    """
    started_at = datetime.now(timezone.utc)
    started_perf = time.perf_counter()
    outcome = sync_iniciadores_reinspeccion_notificacion()
    elapsed_ms = round((time.perf_counter() - started_perf) * 1000, 2)

    return {
        "status": "ok",
        "created": int(outcome.created),
        "eligible_notificaciones": int(outcome.eligible_notificaciones),
        "skipped_already_blocking": int(outcome.skipped_already_blocking),
        "collisions_idempotent": int(outcome.collisions_idempotent),
        "elapsed_ms": elapsed_ms,
        "started_at": started_at.isoformat(),
    }


def main() -> None:
    """
    Punto de entrada CLI para sincronizar notificaciones vencidas.

    Uso: `python -m app.domains.actuaciones.pipelines.sync_notificaciones_vencidas`
    o `flask sync-notificaciones-vencidas` (ver `create_app`).
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from app.main import create_app

    app = create_app()
    with app.app_context():
        try:
            metrics = run_sync_notificaciones_vencidas()
        except Exception:
            logger.exception("run_sync_notificaciones_vencidas: falló")
            sys.exit(1)
        print(
            "Sync notificaciones vencidas OK. "
            f"created={metrics['created']} eligible={metrics['eligible_notificaciones']} "
            f"skipped_blocking={metrics['skipped_already_blocking']} collisions={metrics['collisions_idempotent']} "
            f"elapsed_ms={metrics['elapsed_ms']}"
        )
        print(json.dumps(metrics, ensure_ascii=True))


if __name__ == "__main__":
    main()
