from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone

from app.domains.actuaciones.services.notificacion_iniciador_service import (
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.rutas_trabajo.services.auth_service import validate_actor_user_id

logger = logging.getLogger(__name__)


def run_sync_notificaciones_vencidas(*, actor_user_id: int) -> dict[str, int | float | str]:
    """
    Ejecuta el sync de iniciadores por notificaciones vencidas (camino canónico operativo, Fase C).

    Parámetros:
        actor_user_id: usuario que audita la corrida (obligatorio).

    Returns:
        Métricas operativas de la corrida.

    Errores:
        ValueError: actor inválido.
    """
    validate_actor_user_id(actor_user_id)
    started_at = datetime.now(timezone.utc)
    started_perf = time.perf_counter()
    outcome = sync_iniciadores_reinspeccion_notificacion(actor_user_id=actor_user_id)
    elapsed_ms = round((time.perf_counter() - started_perf) * 1000, 2)

    return {
        "status": "ok",
        "actor_user_id": int(actor_user_id),
        "created": int(outcome.created),
        "eligible_notificaciones": int(outcome.eligible_notificaciones),
        "skipped_already_blocking": int(outcome.skipped_already_blocking),
        "collisions_idempotent": int(outcome.collisions_idempotent),
        "revoked": int(outcome.revoked),
        "elapsed_ms": elapsed_ms,
        "started_at": started_at.isoformat(),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sincroniza iniciadores REINSPECCION_NOTIFICACION por notificaciones vencidas."
    )
    parser.add_argument(
        "--actor-user-id",
        type=int,
        required=True,
        help="ID de usuario activo que audita la corrida (obligatorio).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """
    Punto de entrada CLI para sincronizar notificaciones vencidas.

    Uso: `python -m app.domains.actuaciones.pipelines.sync_notificaciones_vencidas --actor-user-id 124`
    o `flask sync-notificaciones-vencidas --actor-user-id 124` (ver `create_app`).
    """
    args = _parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from app.main import create_app

    app = create_app()
    with app.app_context():
        try:
            validate_actor_user_id(args.actor_user_id)
        except ValueError as exc:
            logger.error("%s", exc)
            sys.exit(1)
        try:
            metrics = run_sync_notificaciones_vencidas(actor_user_id=args.actor_user_id)
        except Exception:
            logger.exception("run_sync_notificaciones_vencidas: falló")
            sys.exit(1)
        print(
            "Sync notificaciones vencidas OK. "
            f"actor_user_id={metrics['actor_user_id']} "
            f"created={metrics['created']} eligible={metrics['eligible_notificaciones']} "
            f"skipped_blocking={metrics['skipped_already_blocking']} collisions={metrics['collisions_idempotent']} "
            f"revoked={metrics['revoked']} "
            f"elapsed_ms={metrics['elapsed_ms']}"
        )
        print(json.dumps(metrics, ensure_ascii=True))


if __name__ == "__main__":
    main()
