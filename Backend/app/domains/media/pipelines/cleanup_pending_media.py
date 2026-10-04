"""Pipeline operativo: limpieza diaria de cargas PENDING abandonadas."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from app.domains.media.schemas.cleanup_schemas import CleanupPendingMediaResult
from app.domains.media.services.cleanup_pending_media_service import cleanup_pending_media

logger = logging.getLogger(__name__)


def run_cleanup_pending_media(*, older_than_hours: int = 24) -> CleanupPendingMediaResult:
    """
    Ejecuta cleanup de archivos PENDING vencidos (fuera del request lifecycle).

    Parámetros:
        older_than_hours: antigüedad mínima en horas.

    Retorno:
        CleanupPendingMediaResult con contadores.
    """
    return cleanup_pending_media(older_than_hours=older_than_hours)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Limpia archivos Media PENDING abandonados.")
    parser.add_argument(
        "--older-than-hours",
        type=int,
        default=24,
        help="Antigüedad mínima en horas (default 24).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada CLI (`python -m app.domains.media.pipelines.cleanup_pending_media`)."""
    args = _parse_args(argv)
    try:
        result = run_cleanup_pending_media(older_than_hours=int(args.older_than_hours))
    except Exception:
        logger.exception("cleanup_pending_media pipeline failed")
        return 1
    payload = result.model_dump()
    print(
        f"Cleanup pending media OK. processed={result.processed} "
        f"storage_delete_errors={result.storage_delete_errors}"
    )
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
