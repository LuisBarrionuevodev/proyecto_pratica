"""
OPER-RUTA.7A — Mediciones temporales de planificación (M3/M4).

Activar con ``PLANIFICACION_DEBUG=1``. No altera reglas de negocio.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger(__name__)


def planificacion_debug_habilitado() -> bool:
    """True si deben emitirse logs OPER-RUTA.7A."""
    return os.environ.get("PLANIFICACION_DEBUG", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def log_oper_ruta_7a(tag: str, **campos) -> None:
    """
    Emite una línea estructurada ``[OPER_RUTA_7A_*]`` si debug está habilitado.

    Parámetros:
        tag: sufijo del tag (M4, URGENTES, etc.).
        **campos: pares clave=valor en el log.
    """
    if not planificacion_debug_habilitado():
        return
    parts = " ".join(f"{k}={v}" for k, v in campos.items())
    logger.warning("[OPER_RUTA_7A_%s] %s", tag, parts)


@contextmanager
def medir_oper_ruta_7a(tag: str, **campos_base) -> Iterator[dict]:
    """
    Context manager que mide elapsed_ms y emite log al salir.

    Yields:
        dict mutable para agregar contadores antes del log final.
    """
    stats: dict = dict(campos_base)
    t0 = time.perf_counter()
    try:
        yield stats
    finally:
        stats["total_ms"] = int((time.perf_counter() - t0) * 1000)
        log_oper_ruta_7a(tag, **stats)
