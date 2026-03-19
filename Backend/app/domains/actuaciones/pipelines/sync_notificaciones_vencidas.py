from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from app.domains.actuaciones.services.notificacion_iniciador_service import (
    sync_iniciadores_reinspeccion_notificacion,
)


def run_sync_notificaciones_vencidas() -> dict[str, int | float | str]:
    """
    Ejecuta el sync de iniciadores por notificaciones vencidas.

    Returns:
        Métricas operativas de la corrida.
    """
    started_at = datetime.now(timezone.utc)
    started_perf = time.perf_counter()
    created = sync_iniciadores_reinspeccion_notificacion()
    elapsed_ms = round((time.perf_counter() - started_perf) * 1000, 2)

    return {
        "status": "ok",
        "created": int(created),
        "elapsed_ms": elapsed_ms,
        "started_at": started_at.isoformat(),
    }


def main() -> None:
    """
    Punto de entrada CLI para sincronizar notificaciones vencidas.
    """
    from app.main import create_app

    app = create_app()
    with app.app_context():
        metrics = run_sync_notificaciones_vencidas()
        print(
            "Sync notificaciones vencidas OK. "
            f"created={metrics['created']} elapsed_ms={metrics['elapsed_ms']}"
        )
        print(json.dumps(metrics, ensure_ascii=True))


if __name__ == "__main__":
    main()
