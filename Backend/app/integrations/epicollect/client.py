"""
Cliente HTTP de solo lectura contra la API de exportación de entries de EpiCollect5.

Documentación: https://developers.epicollect.net/entries/entries
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Tuple

from .config import EpicollectClientConfig
from .errors import (
    EpicollectAuthError,
    EpicollectConfigError,
    EpicollectEntryNotFoundError,
    EpicollectHttpError,
    EpicollectNetworkError,
)

logger = logging.getLogger(__name__)

_JSON_HEADERS = {
    "Accept": "application/json",
}


def parse_export_entries_response(body: Any) -> List[Dict[str, Any]]:
    """
    Extrae la lista de entries del JSON de ``GET /api/export/entries/...``.

    Soporta el envelope documentado (``data.entries``) y variantes con ``data`` como lista.

    Args:
        body: Objeto parseado de la respuesta (dict).

    Returns:
        Lista de dicts (entries); puede estar vacía.
    """
    if not isinstance(body, dict):
        return []
    data = body.get("data")
    if isinstance(data, dict):
        entries = data.get("entries")
        if isinstance(entries, list):
            return [e for e in entries if isinstance(e, dict)]
    if isinstance(data, list):
        return [e for e in data if isinstance(e, dict)]
    return []


class EpicollectApiClient:
    """
    Encapsula requests a EpiCollect5 (token OAuth opcional + export entries).

    Args:
        config: Parámetros de proyecto y credenciales.
        session: Sesión ``requests`` inyectable para tests.
    """

    def __init__(
        self,
        config: EpicollectClientConfig,
        session: "requests.Session | None" = None,
    ) -> None:
        self._config = config
        if session is not None:
            self._session = session
        else:
            import requests

            self._session = requests.Session()
        self._access_token: str | None = None
        self._token_expires_at_monotonic: float = 0.0

    @classmethod
    def from_app_config(cls, config_mapping: dict[str, Any]) -> EpicollectApiClient:
        """
        Crea el cliente desde ``current_app.config`` u otro dict con claves EPICOLLECT_*.

        Raises:
            EpicollectConfigError: configuración inválida o incompleta.
        """
        return cls(EpicollectClientConfig.from_mapping(config_mapping))

    def _entries_url(self) -> str:
        return f"{self._config.base_url}/api/export/entries/{self._config.project_slug}"

    def _oauth_token_url(self) -> str:
        return f"{self._config.base_url}/api/oauth/token"

    def _refresh_oauth_token(self) -> None:
        import requests

        if not self._config.client_id or not self._config.client_secret:
            raise EpicollectAuthError("EpiCollect: OAuth requerido pero faltan credenciales.")
        url = self._oauth_token_url()
        payload = {
            "grant_type": "client_credentials",
            "client_id": int(self._config.client_id)
            if str(self._config.client_id).isdigit()
            else self._config.client_id,
            "client_secret": self._config.client_secret,
        }
        try:
            resp = self._session.post(
                url,
                json=payload,
                headers={**_JSON_HEADERS, "Content-Type": "application/vnd.api+json"},
                timeout=self._config.timeout_seconds,
            )
        except requests.Timeout as e:
            raise EpicollectNetworkError("EpiCollect: timeout al obtener token OAuth.") from e
        except requests.RequestException as e:
            raise EpicollectNetworkError(f"EpiCollect: error de red al obtener token: {e}") from e

        if resp.status_code >= 400:
            raise EpicollectAuthError(
                f"EpiCollect: token OAuth rechazado (HTTP {resp.status_code})."
            )

        try:
            data = resp.json()
        except ValueError as e:
            raise EpicollectAuthError("EpiCollect: respuesta de token no es JSON válido.") from e

        token = data.get("access_token")
        if not token or not isinstance(token, str):
            raise EpicollectAuthError("EpiCollect: respuesta de token sin access_token.")

        self._access_token = token
        expires_in = data.get("expires_in")
        try:
            ttl = float(expires_in) if expires_in is not None else 7200.0
        except (TypeError, ValueError):
            ttl = 7200.0
        # Margen para no usar token al límite
        self._token_expires_at_monotonic = time.monotonic() + max(60.0, ttl - 120.0)

    def _ensure_access_token(self) -> None:
        if not self._config.uses_oauth:
            return
        if self._access_token and time.monotonic() < self._token_expires_at_monotonic:
            return
        self._refresh_oauth_token()

    def _auth_headers(self) -> Dict[str, str]:
        h = dict(_JSON_HEADERS)
        if self._config.uses_oauth:
            self._ensure_access_token()
            assert self._access_token
            h["Authorization"] = f"Bearer {self._access_token}"
        return h

    def _get_json(self, url: str, params: Dict[str, Any]) -> Any:
        import requests

        self._ensure_access_token()
        try:
            resp = self._session.get(
                url,
                params=params,
                headers=self._auth_headers(),
                timeout=self._config.timeout_seconds,
            )
        except requests.Timeout as e:
            raise EpicollectNetworkError(f"EpiCollect: timeout GET {url}") from e
        except requests.RequestException as e:
            raise EpicollectNetworkError(f"EpiCollect: error de red: {e}") from e

        if resp.status_code == 401 and self._config.uses_oauth:
            logger.info("EpiCollect: 401 en export; refrescando token OAuth.")
            self._access_token = None
            self._refresh_oauth_token()
            try:
                resp = self._session.get(
                    url,
                    params=params,
                    headers=self._auth_headers(),
                    timeout=self._config.timeout_seconds,
                )
            except requests.Timeout as e:
                raise EpicollectNetworkError(f"EpiCollect: timeout GET (reintento) {url}") from e
            except requests.RequestException as e:
                raise EpicollectNetworkError(f"EpiCollect: error de red (reintento): {e}") from e

        if resp.status_code >= 400:
            raise EpicollectHttpError(
                f"EpiCollect: HTTP {resp.status_code} al consultar entries.",
                status_code=resp.status_code,
            )

        try:
            return resp.json()
        except ValueError as e:
            raise EpicollectHttpError(
                "EpiCollect: cuerpo de respuesta no es JSON válido.",
                status_code=resp.status_code,
            ) from e

    def fetch_entry_dict_by_uuid(self, ec5_uuid: str) -> Dict[str, Any]:
        """
        Obtiene un único entry por UUID (parámetro ``uuid`` del export API).

        Args:
            ec5_uuid: UUID canónico del entry (string).

        Returns:
            Dict del entry listo para pasar a ``import_epicollect_entry``.

        Raises:
            EpicollectEntryNotFoundError: lista vacía.
            EpicollectHttpError, EpicollectNetworkError, EpicollectAuthError: según fallo HTTP/red.
        """
        params: Dict[str, Any] = {
            "uuid": ec5_uuid,
            "per_page": 1,
            "page": 1,
            "format": "json",
        }
        if self._config.form_ref:
            params["form_ref"] = self._config.form_ref

        body = self._get_json(self._entries_url(), params)
        entries = parse_export_entries_response(body)
        if not entries:
            raise EpicollectEntryNotFoundError(
                f"EpiCollect: no se encontró entry con uuid={ec5_uuid} en el proyecto configurado."
            )
        return entries[0]

    def list_entries_page(
        self,
        *,
        page: int = 1,
        per_page: int = 50,
        filter_by: str | None = None,
        filter_from: str | None = None,
        filter_to: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Una página de entries (para inspección o futuras herramientas; no import masivo aquí).

        Args:
            page: Página 1-based.
            per_page: Tamaño de página (máx. 1000 en API).
            filter_by: ``created_at`` o ``uploaded_at`` si aplica.
            filter_from / filter_to: ISO 8601 según documentación EpiCollect.
            sort_by / sort_order: columnas permitidas por la API.

        Returns:
            (entries, meta) donde ``meta`` incluye fragmentos útiles de ``body.get("meta")``.

        Raises:
            EpicollectConfigError: si ``project_slug`` inválido (ya validado en config).
            EpicollectHttpError, EpicollectNetworkError, EpicollectAuthError: fallos HTTP/red.
        """
        per_page = max(1, min(1000, int(per_page)))
        page = max(1, int(page))
        params: Dict[str, Any] = {
            "per_page": per_page,
            "page": page,
            "format": "json",
        }
        if self._config.form_ref:
            params["form_ref"] = self._config.form_ref
        if filter_by:
            params["filter_by"] = filter_by
        if filter_from:
            params["filter_from"] = filter_from
        if filter_to:
            params["filter_to"] = filter_to
        if sort_by:
            params["sort_by"] = sort_by
        if sort_order:
            params["sort_order"] = sort_order

        body = self._get_json(self._entries_url(), params)
        entries = parse_export_entries_response(body)
        meta = body.get("meta") if isinstance(body, dict) else None
        meta_out: Dict[str, Any] = meta if isinstance(meta, dict) else {}
        return entries, meta_out
