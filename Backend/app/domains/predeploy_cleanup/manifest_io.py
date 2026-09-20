"""Carga, validación y hashing de manifests de cleanup/preprotección."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ManifestError(Exception):
    """Error de validación o carga de manifest."""


def file_sha256(path: Path) -> str:
    """Calcula SHA-256 de un archivo."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_sha256(data: dict[str, Any]) -> str:
    """Hash estable del contenido JSON (sin campo hash embebido)."""
    payload = {
        k: v
        for k, v in data.items()
        if k not in ("manifest_sha256", "execution_manifest_hash")
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    """Carga manifest JSON desde disco."""
    if not path.is_file():
        raise ManifestError(f"Manifest no encontrado: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Manifest JSON inválido: {path}") from exc


def entity_ids(manifest: dict[str, Any], entity: str) -> set[int]:
    """Extrae IDs enteros de una entidad del manifest."""
    entries = manifest.get("entities", {}).get(entity, [])
    if not entries:
        entries = manifest.get(entity, [])
    ids: set[int] = set()
    for item in entries:
        if isinstance(item, int):
            ids.add(item)
        elif isinstance(item, dict) and "id" in item:
            ids.add(int(item["id"]))
    return ids


def validate_ids_exist(
    conn,
    table: str,
    ids: set[int],
    *,
    label: str,
) -> list[dict[str, Any]]:
    """
    Verifica que los IDs existan en DB.

    Retorna lista de STALE_PROTECTED_ID para los ausentes.
    """
    if not ids:
        return []
    from sqlalchemy import text

    stale: list[dict[str, Any]] = []
    id_list = sorted(ids)
    chunk = 500
    for i in range(0, len(id_list), chunk):
        part = id_list[i : i + chunk]
        ph = ",".join(str(x) for x in part)
        found = {
            row[0]
            for row in conn.execute(text(f"SELECT id FROM `{table}` WHERE id IN ({ph})"))
        }
        for missing in set(part) - found:
            stale.append({"entity": label, "table": table, "id": missing, "status": "STALE_PROTECTED_ID"})
    return stale
