"""
Extracción de UUID de entry y valores de campos desde JSON EpiCollect5.

Soporta formas habituales (raíz o anidado bajo `data` / `entry`).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Collection
from typing import Any, Dict, Iterator
from urllib.parse import urlparse

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

_EXT_TO_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
}


def normalize_uuid_string(value: Any) -> str | None:
    """Devuelve UUID canónico en minúsculas o None si no es válido."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or not _UUID_RE.match(s):
        return None
    try:
        return str(uuid.UUID(s))
    except ValueError:
        return None


def coalesce_epicollect_entry_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Alinea el shape del JSON con lo que esperan UUID, campos y snapshot no-media.

    Algunos exports de la API devuelven ``{"data": [<entry_dict>, ...]}`` (lista).
    El import asume un único dict con ``ec5_uuid`` / campos del formulario en la raíz.

    Args:
        payload: Objeto crudo (p. ej. cuerpo bajo ``payload`` del POST).

    Returns:
        El primer elemento de ``payload["data"]`` si es una lista no vacía de dicts;
        en caso contrario ``payload`` sin modificar.

    Nota:
        Si la lista tiene más de un entry, solo se usa el primero (un POST = un entry).
    """
    data = payload.get("data")
    if isinstance(data, list) and len(data) >= 1 and isinstance(data[0], dict):
        return data[0]
    return payload


def extract_ec5_entry_uuid(payload: dict[str, Any]) -> str:
    """
    Obtiene el UUID del entry desde el payload crudo de EpiCollect.

    Prueba claves comunes en la raíz y en subdicts `data`, `entry`, `values`.

    Raises:
        ValueError: si no se encuentra un UUID válido.
    """
    if not isinstance(payload, dict):
        raise ValueError("EpiCollect: el payload debe ser un objeto JSON.")

    candidates: list[Any] = []
    for key in ("uuid", "entry_uuid", "ec5_uuid", "id", "entryId", "entry_id"):
        if key in payload:
            candidates.append(payload.get(key))

    for nest_key in ("data", "entry", "values"):
        nested = payload.get(nest_key)
        if isinstance(nested, dict):
            for key in ("uuid", "entry_uuid", "ec5_uuid", "id"):
                if key in nested:
                    candidates.append(nested.get(key))

    for c in candidates:
        norm = normalize_uuid_string(c)
        if norm:
            return norm

    raise ValueError(
        "EpiCollect: no se encontró un UUID de entry válido en el payload "
        "(se esperaba en uuid, id, data.uuid, etc.)."
    )


def resolve_field_raw(payload: dict[str, Any], field_id: str) -> Any:
    """
    Obtiene el valor crudo de un campo del formulario.

    Orden: raíz, luego `data`, `entry`, `values` si son dict.
    """
    if field_id in payload:
        return payload[field_id]
    for nest_key in ("data", "entry", "values"):
        nested = payload.get(nest_key)
        if isinstance(nested, dict) and field_id in nested:
            return nested[field_id]
    return None


def _is_http_url(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    p = urlparse(s)
    return p.scheme in ("http", "https") and bool(p.netloc)


def iter_media_urls(value: Any) -> Iterator[str]:
    """
    Normaliza un valor de campo EpiCollect a cero o más URLs http(s).

    Ignora: None, strings vacíos o solo espacios, entradas nulas en listas.

    Acepta: str URL, lista de str / dicts anidados, dict con `url`/`href`/`file`/`path`.
    """
    if value is None:
        return
    if isinstance(value, str):
        if _is_http_url(value):
            yield value.strip()
        return
    if isinstance(value, dict):
        for k in ("url", "href", "URL", "file", "path"):
            inner = value.get(k)
            if isinstance(inner, str) and _is_http_url(inner):
                yield inner.strip()
                return
        return
    if isinstance(value, list):
        for item in value:
            if item is None:
                continue
            yield from iter_media_urls(item)


def build_payload_non_media_envelope(
    payload: Dict[str, Any],
    media_field_ids: Collection[str],
) -> Dict[str, Any]:
    """
    Arma el JSON persistible de respuestas de formulario sin campos de media (allowlist).

    Estructura guardada: ``{"data": { ... }}`` para alinear con el shape típico de EpiCollect
    y dejar margen a claves hermanas futuras (p. ej. meta) sin migración.

    - Si existe ``payload["data"]`` como dict: copia claves que no están en ``media_field_ids``.
    - Si no hay ``data``: copia superficial de la raíz excluyendo claves técnicas habituales
      y la allowlist de media (fallback para exports atípicos).

    No aplica heurística de URL: solo excluye por id de campo de la allowlist de fotos/archivos.
    """
    media_ids = frozenset(media_field_ids)
    if isinstance(payload.get("data"), dict):
        data = payload["data"]
        stripped = {k: v for k, v in data.items() if k not in media_ids}
        return {"data": stripped}

    skip_root = media_ids | {
        "data",
        "entry",
        "values",
        "uuid",
        "entry_uuid",
        "ec5_uuid",
        "id",
        "entryId",
        "entry_id",
    }
    stripped = {k: v for k, v in payload.items() if k not in skip_root}
    return {"data": stripped}


def guess_mime_type_from_url(url: str) -> str | None:
    """Inferencia ligera por extensión del path (sin HEAD request)."""
    try:
        path = urlparse(url).path.lower()
    except Exception:
        return None
    for ext, mime in _EXT_TO_MIME.items():
        if path.endswith(ext):
            return mime
    return None
