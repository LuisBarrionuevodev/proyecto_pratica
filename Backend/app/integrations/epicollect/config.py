"""
Configuración del cliente EpiCollect desde variables de entorno / Flask config.

Variables soportadas (env o ``app.config`` con el mismo nombre en mayúsculas):

- ``EPICOLLECT_BASE_URL``: host API (default ``https://five.epicollect.net``).
- ``EPICOLLECT_PROJECT_SLUG``: slug del proyecto (obligatorio para llamadas).
- ``EPICOLLECT_FORM_REF``: ref del formulario (opcional; si falta, usa el primero del proyecto).
- ``EPICOLLECT_CLIENT_ID`` / ``EPICOLLECT_CLIENT_SECRET``: OAuth client credentials
  para proyectos privados; si ambos están vacíos, se asume proyecto público.
- ``EPICOLLECT_TIMEOUT_SECONDS``: timeout total por request HTTP (default 30).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from .errors import EpicollectConfigError


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class EpicollectClientConfig:
    """Parámetros inmutables para ``EpicollectApiClient``."""

    base_url: str
    project_slug: str
    form_ref: str | None
    client_id: str | None
    client_secret: str | None
    timeout_seconds: float

    @property
    def uses_oauth(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @classmethod
    def from_mapping(cls, m: dict[str, Any]) -> EpicollectClientConfig:
        """
        Construye config desde un dict (típicamente ``current_app.config`` mezclado con os.environ).

        Raises:
            EpicollectConfigError: si falta ``project_slug``.
        """
        base = (m.get("EPICOLLECT_BASE_URL") or os.getenv("EPICOLLECT_BASE_URL") or "").strip()
        if not base:
            base = "https://five.epicollect.net"
        slug = (m.get("EPICOLLECT_PROJECT_SLUG") or os.getenv("EPICOLLECT_PROJECT_SLUG") or "").strip()
        if not slug:
            raise EpicollectConfigError(
                "EpiCollect: falta EPICOLLECT_PROJECT_SLUG (slug del proyecto en EpiCollect5)."
            )
        form_ref_raw = m.get("EPICOLLECT_FORM_REF") or os.getenv("EPICOLLECT_FORM_REF")
        form_ref = str(form_ref_raw).strip() if form_ref_raw else None
        form_ref = form_ref or None

        cid = (m.get("EPICOLLECT_CLIENT_ID") or os.getenv("EPICOLLECT_CLIENT_ID") or "").strip() or None
        csec = (
            (m.get("EPICOLLECT_CLIENT_SECRET") or os.getenv("EPICOLLECT_CLIENT_SECRET") or "").strip()
            or None
        )
        if (cid and not csec) or (csec and not cid):
            raise EpicollectConfigError(
                "EpiCollect: EPICOLLECT_CLIENT_ID y EPICOLLECT_CLIENT_SECRET deben ir ambos "
                "definidos o ambos vacíos (proyecto público)."
            )

        timeout = m.get("EPICOLLECT_TIMEOUT_SECONDS")
        if timeout is None:
            timeout = _env_float("EPICOLLECT_TIMEOUT_SECONDS", 30.0)
        else:
            try:
                timeout = float(timeout)
            except (TypeError, ValueError):
                timeout = 30.0

        return cls(
            base_url=base.rstrip("/"),
            project_slug=slug,
            form_ref=form_ref,
            client_id=cid,
            client_secret=csec,
            timeout_seconds=max(5.0, timeout),
        )
