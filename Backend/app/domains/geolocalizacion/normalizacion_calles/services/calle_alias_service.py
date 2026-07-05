"""
Resolución de alias/variantes de calle desde CSV local (PR4).

Sin migración DB: ``calle_aliases.csv`` mapea alias → ``nombre_canonico`` del catálogo.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import (
    preprocess_street_input,
    slug_key,
    street_base,
)

_ALIASES_CSV = Path(__file__).resolve().parents[1] / "data" / "calle_aliases.csv"


@lru_cache(maxsize=1)
def _load_alias_map() -> dict[str, str]:
    """
    Carga alias → nombre_canonico (keys normalizadas con ``slug_key``).

    Retorno:
        Mapa alias_key → nombre_canonico literal del catálogo.
    """
    mapping: dict[str, str] = {}
    if not _ALIASES_CSV.is_file():
        return mapping
    with _ALIASES_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alias = (row.get("alias") or "").strip()
            canon = (row.get("nombre_canonico") or "").strip()
            if not alias or not canon:
                continue
            for variant in (alias, preprocess_street_input(alias)):
                key = slug_key(variant)
                if key:
                    mapping[key] = canon
            base = street_base(alias)
            if base:
                mapping[slug_key(base)] = canon
    return mapping


def reload_calle_aliases_cache() -> None:
    """Invalida cache en memoria (tests o recarga CSV)."""
    _load_alias_map.cache_clear()


def resolve_calle_alias(nombre_input: str) -> str | None:
    """
    Resuelve alias conocido a ``nombre_canonico`` del catálogo.

    Parámetros:
        nombre_input: texto crudo del usuario.

    Retorno:
        Nombre canónico del catálogo o None si no hay alias.
    """
    if not nombre_input or not str(nombre_input).strip():
        return None
    mapping = _load_alias_map()
    for candidate in (
        slug_key(nombre_input),
        slug_key(preprocess_street_input(nombre_input)),
        slug_key(street_base(nombre_input)),
    ):
        if candidate and candidate in mapping:
            return mapping[candidate]
    return None
