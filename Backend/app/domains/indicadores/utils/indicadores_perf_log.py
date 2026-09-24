"""
Logs de performance para endpoints de indicadores (diagnóstico IND-BE.1).

Activar con ``PERF_LOG=1`` (misma variable que ``app.shared.perf_log``).
Sin flag: cero overhead (early return).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from app.shared.perf_log import PerfTimer, perf_log_enabled

logger = logging.getLogger(__name__)

__all__ = [
    "PerfTimer",
    "log_indicadores_endpoint",
    "log_indicadores_query",
    "perf_log_enabled",
]


def _fmt_date(value: date | str) -> str:
    return value.isoformat() if isinstance(value, date) else str(value)


def _fmt_optional_id(value: Optional[int]) -> str:
    return str(value) if value is not None else "all"


def log_indicadores_endpoint(
    endpoint: str,
    *,
    total_ms: float,
    desde: date | str,
    hasta: date | str,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    **extra: Any,
) -> None:
    """
    Log de tiempo total de un endpoint de indicadores.

    Formato:
        [PERF][indicadores][productividad] total=1234ms desde=... hasta=... distrito=... inspector=...
    """
    if not perf_log_enabled():
        return
    extra_s = " ".join(f"{k}={v}" for k, v in extra.items() if v is not None)
    logger.info(
        "[PERF][indicadores][%s] total=%sms desde=%s hasta=%s distrito=%s inspector=%s%s",
        endpoint,
        round(total_ms, 1),
        _fmt_date(desde),
        _fmt_date(hasta),
        _fmt_optional_id(distrito_id),
        _fmt_optional_id(inspector_id),
        f" {extra_s}" if extra_s else "",
    )


def log_indicadores_query(subkey: str, query_ms: float, **extra: Any) -> None:
    """
    Log de tiempo de una query interna.

    Formato:
        [PERF][indicadores][productividad.realizadas] query=420ms
    """
    if not perf_log_enabled():
        return
    extra_s = " ".join(f"{k}={v}" for k, v in extra.items() if v is not None)
    logger.info(
        "[PERF][indicadores][%s] query=%sms%s",
        subkey,
        round(query_ms, 1),
        f" {extra_s}" if extra_s else "",
    )
