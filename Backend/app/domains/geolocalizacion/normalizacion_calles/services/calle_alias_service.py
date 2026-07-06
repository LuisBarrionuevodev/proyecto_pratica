"""
Resolución de alias/variantes de calle desde CSV local (PR4/PR5b).

El CSV es apoyo operativo; la fuente oficial es ``calle_catalogo`` en DB.
Solo se aplican alias cuyo ``nombre_canonico`` exista en catálogo activo.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.domains.geolocalizacion.normalizacion_calles.repos.calle_catalogo_repo import (
    get_by_nombre_canonico,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import (
    preprocess_street_input,
    slug_key,
    street_base,
)

_ALIASES_CSV = Path(__file__).resolve().parents[1] / "data" / "calle_aliases.csv"


@dataclass
class _AliasCacheState:
    """Cache en memoria de alias validados contra catálogo DB."""

    mapping: dict[str, str]
    valid_rows: list[dict[str, str]]
    invalid_rows: list[dict[str, str]]


_alias_cache: _AliasCacheState | None = None


def _read_csv_rows() -> list[dict[str, str]]:
    """
    Lee filas crudas del CSV de alias.

    Retorno:
        Lista de dicts ``alias``, ``nombre_canonico``, ``notas``.
    """
    if not _ALIASES_CSV.is_file():
        return []
    rows: list[dict[str, str]] = []
    with _ALIASES_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            alias = (row.get("alias") or "").strip()
            canon = (row.get("nombre_canonico") or "").strip()
            if not alias or not canon:
                continue
            rows.append(
                {
                    "alias": alias,
                    "nombre_canonico": canon,
                    "notas": (row.get("notas") or "").strip(),
                }
            )
    return rows


def _build_validated_cache() -> _AliasCacheState:
    """
    Construye mapa alias→canon solo para filas con canon en ``calle_catalogo``.

    Retorno:
        Estado con mapping, filas válidas e inválidas.
    """
    mapping: dict[str, str] = {}
    valid_rows: list[dict[str, str]] = []
    invalid_rows: list[dict[str, str]] = []

    for row in _read_csv_rows():
        alias = row["alias"]
        canon = row["nombre_canonico"]
        catalog_row = get_by_nombre_canonico(canon)
        if catalog_row is None:
            invalid_rows.append(
                {
                    **row,
                    "reason": "nombre_canonico no existe en calle_catalogo activo",
                }
            )
            continue
        valid_rows.append(row)
        for variant in (alias, preprocess_street_input(alias)):
            key = slug_key(variant)
            if key:
                mapping[key] = catalog_row.nombre_canonico
        base = street_base(alias)
        if base:
            mapping[slug_key(base)] = catalog_row.nombre_canonico

    return _AliasCacheState(mapping=mapping, valid_rows=valid_rows, invalid_rows=invalid_rows)


def _ensure_alias_cache() -> _AliasCacheState:
    """Carga cache validada bajo demanda (requiere app context / DB)."""
    global _alias_cache
    if _alias_cache is None:
        _alias_cache = _build_validated_cache()
    return _alias_cache


def reload_calle_aliases_cache() -> None:
    """Invalida cache en memoria (tests o recarga CSV)."""
    global _alias_cache
    _alias_cache = None


def resolve_calle_alias(nombre_input: str) -> str | None:
    """
    Resuelve alias conocido a ``nombre_canonico`` del catálogo DB.

    Solo devuelve alias validados contra ``calle_catalogo``.

    Parámetros:
        nombre_input: texto crudo del usuario.

    Retorno:
        Nombre canónico del catálogo o None si no hay alias válido.
    """
    if not nombre_input or not str(nombre_input).strip():
        return None
    mapping = _ensure_alias_cache().mapping
    for candidate in (
        slug_key(nombre_input),
        slug_key(preprocess_street_input(nombre_input)),
        slug_key(street_base(nombre_input)),
    ):
        if candidate and candidate in mapping:
            return mapping[candidate]
    return None


def audit_calle_aliases() -> dict[str, Any]:
    """
    Audita filas del CSV contra ``calle_catalogo``.

    Retorno:
        ``{valid, invalid, valid_count, invalid_count, csv_path}``.
    """
    state = _ensure_alias_cache()
    return {
        "csv_path": str(_ALIASES_CSV),
        "valid": list(state.valid_rows),
        "invalid": list(state.invalid_rows),
        "valid_count": len(state.valid_rows),
        "invalid_count": len(state.invalid_rows),
    }
