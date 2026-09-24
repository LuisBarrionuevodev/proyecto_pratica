"""
Diagnóstico dev: identifica clientes que hacen POST a la raíz (404 habitual).

Activar en desarrollo con FLASK_ENV=development (por defecto).
Desactivar: FLASK_LOG_POST_ROOT=0
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from flask import Flask, request

logger = logging.getLogger(__name__)

_last_post_root_log_at = 0.0
_post_root_burst_count = 0


def _enabled() -> bool:
    if os.getenv("FLASK_LOG_POST_ROOT", "1").strip().lower() in {"0", "false", "no", "off"}:
        return False
    return os.getenv("FLASK_ENV", "development").lower() == "development"


def _peek_body(max_len: int = 200) -> str:
    """Muestra un fragmento del body sin romper el stream de la petición."""
    try:
        raw = request.get_data(cache=True, as_text=True) or ""
        one_line = " ".join(raw.split())
        if len(one_line) > max_len:
            return one_line[:max_len] + "…"
        return one_line or "(vacío)"
    except Exception as exc:  # noqa: BLE001
        return f"(no legible: {exc})"


def register_dev_post_root_logger(app: Flask) -> None:
    """
    Registra hook que loguea metadatos de POST / (ruta inexistente).

    Parámetros:
        app: aplicación Flask.
    """

    @app.before_request
    def _log_post_root_client() -> None:
        global _last_post_root_log_at, _post_root_burst_count

        if not _enabled():
            return None
        if request.method != "POST" or request.path != "/":
            return None

        _post_root_burst_count += 1
        now = time.monotonic()
        if now - _last_post_root_log_at < 2.0:
            return None

        burst = _post_root_burst_count
        _post_root_burst_count = 0
        _last_post_root_log_at = now

        meta: dict[str, Any] = {
            "burst_en_2s": burst,
            "remote_addr": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", "—"),
            "referer": request.headers.get("Referer", "—"),
            "origin": request.headers.get("Origin", "—"),
            "content_type": request.headers.get("Content-Type", "—"),
            "content_length": request.headers.get("Content-Length", "—"),
            "host": request.headers.get("Host", "—"),
            "body_preview": _peek_body(),
        }
        logger.warning(
            "POST / sin ruta (404 esperado). Cliente sospechoso: "
            "burst=%(burst_en_2s)s addr=%(remote_addr)s host=%(host)s "
            "ua=%(user_agent)s referer=%(referer)s origin=%(origin)s "
            "ctype=%(content_type)s clen=%(content_length)s body=%(body_preview)s",
            meta,
        )
        return None
