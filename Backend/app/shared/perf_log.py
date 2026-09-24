"""
Logs temporales de performance para relevamiento QA.

Activar con variable de entorno ``PERF_LOG=1`` (o ``true`` / ``yes``).
Sin flag: cero overhead (early return).
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


def perf_log_enabled() -> bool:
    """True si ``PERF_LOG`` está activo."""
    return os.getenv("PERF_LOG", "").strip().lower() in ("1", "true", "yes")


def perf_endpoint_log(
    endpoint: str,
    *,
    rows_base: int,
    rows_final: int,
    query_ms: float,
    presenter_ms: float,
    total_ms: float,
    payload: Any | None = None,
    **extra: Any,
) -> None:
    """
    Emite un log estructurado de performance para un endpoint HTTP.

    Parámetros:
        endpoint: identificador corto (ej. ``notificaciones.pendientes_expediente``).
        rows_base: filas devueltas por la query principal.
        rows_final: filas en la respuesta JSON.
        query_ms: tiempo de consulta ORM/SQL.
        presenter_ms: tiempo de batch maps + presenters.
        total_ms: tiempo total del handler.
        payload: cuerpo serializable para estimar tamaño de respuesta.
        **extra: pares adicionales (source_type, omitir_rango_fecha, etc.).
    """
    if not perf_log_enabled():
        return
    resp_bytes: int | None = None
    if payload is not None:
        try:
            resp_bytes = len(json.dumps(payload, default=str))
        except Exception:
            resp_bytes = None
    extra_s = " ".join(f"{k}={v}" for k, v in extra.items()) if extra else ""
    logger.info(
        "perf.%s rows_base=%s rows_final=%s query_ms=%s presenter_ms=%s total_ms=%s resp_bytes=%s %s",
        endpoint,
        rows_base,
        rows_final,
        round(query_ms, 1),
        round(presenter_ms, 1),
        round(total_ms, 1),
        resp_bytes,
        extra_s.strip(),
    )


class PerfTimer:
    """Cronómetro simple basado en ``time.perf_counter``."""

    def __init__(self) -> None:
        self._t0 = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._t0) * 1000.0

    def reset(self) -> None:
        self._t0 = time.perf_counter()
