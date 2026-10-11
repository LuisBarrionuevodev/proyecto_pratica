"""
Resolución canónica de relevador desde celda de grilla / payload (única fuente de verdad).

Acepta ``Apellido, Nombre`` y ``Nombre Apellido`` (y variantes con tildes/case).
Separador de múltiples relevadores en celda: solo ``;`` (no la coma del formato catálogo).
"""

from __future__ import annotations

import re
from typing import Any, List

from app.domains.relevamientos.utils.relevador_display import (
    relevador_identity_key_from_nombre,
    relevador_nombres_equivalentes,
)
from app.models import Relevador

_MULTI_RELEVADOR_SEP_RE = re.compile(r";")


def _clean_str(v: Any) -> str:
    return ("" if v is None else str(v)).strip()


def parse_relevador_celda_a_nombres(value: Any) -> List[str]:
    """
    Interpreta el valor de celda como uno o más nombres de relevador.

    - ``Apellido, Nombre`` → un solo relevador (la coma no separa personas).
    - Varios relevadores explícitos → separados por ``;`` (legacy, rechazado aguas abajo).
    """
    if value is None or value == "":
        return []
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            s = _clean_str(item)
            if s:
                out.extend(parse_relevador_celda_a_nombres(s))
        return out
    s = _clean_str(value)
    if not s:
        return []
    if ";" in s:
        return [p.strip() for p in _MULTI_RELEVADOR_SEP_RE.split(s) if p.strip()]
    return [s]


def _candidatos_relevador_por_nombre(
    nombre_celda: str,
    catalog: List[Relevador] | None = None,
) -> List[Relevador]:
    """Filas DB que coinciden con el texto de celda (equivalencia apellido/nombre)."""
    rows = catalog if catalog is not None else Relevador.query.all()
    return [r for r in rows if relevador_nombres_equivalentes(r.nombre, nombre_celda)]


def resolve_relevador_unico_por_nombre_celda(
    nombre_celda: str,
    *,
    requiere_activos: bool = True,
    catalog: List[Relevador] | None = None,
) -> Relevador:
    """
    Resuelve un único ``Relevador`` desde texto de celda o catálogo.

    Errores:
        ValueError: no encontrado, inactivo o ambiguo (más de un match en DB).
    """
    s = _clean_str(nombre_celda)
    if not s:
        raise ValueError("Debe indicar un relevador.")

    matches = _candidatos_relevador_por_nombre(s, catalog)
    if len(matches) > 1:
        # Desambiguación por nombre persistido exacto normalizado
        keys = {relevador_identity_key_from_nombre(m.nombre) for m in matches}
        if len(keys) > 1:
            raise ValueError("El relevador es ambiguo. Seleccioná uno del catálogo.")
        matches = matches[:1]

    if len(matches) == 0:
        raise ValueError("Relevador no encontrado. Seleccioná uno del catálogo.")

    row = matches[0]
    if requiere_activos and not row.activo:
        raise ValueError(f"Relevador inactivo: {row.nombre}.")
    return row


def resolve_relevador_nombres_o_falla(
    nombres: List[str],
    *,
    requiere_activos: bool = True,
) -> List[Relevador]:
    """
    Resuelve lista de nombres (0..n) tras ``parse_relevador_celda_a_nombres``.

    Para alta operativa debe haber exactamente un nombre en la lista.
    """
    catalog = Relevador.query.all()
    out: List[Relevador] = []
    seen_keys: set[tuple[str, str]] = set()
    for nombre in nombres:
        row = resolve_relevador_unico_por_nombre_celda(
            nombre, requiere_activos=requiere_activos, catalog=catalog
        )
        key = relevador_identity_key_from_nombre(row.nombre)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        out.append(row)
    return out
