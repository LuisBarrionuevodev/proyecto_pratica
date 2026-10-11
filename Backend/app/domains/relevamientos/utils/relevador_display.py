"""
Etiqueta y orden de catálogo Relevador (campo único ``nombre`` en DB).

Display UI: ``Apellido, Nombre``. Orden: apellido ASC, nombre ASC.
"""

from __future__ import annotations

from app.domains.catalogos.canonical.normalize import normalize_catalog_key

# Nómina canónica (apellido, nombre) — alineada a RELEVADORES_CANONICOS.
_RELEVADOR_PARTS: tuple[tuple[str, str], ...] = (
    ("Esquivel", "Fabian"),
    ("Medina", "Oscar"),
    ("Saravia", "Juan"),
    ("Biscardi", "Roberto"),
    ("Molina", "Antonio"),
    ("Gonzalez", "Guillermo"),
    ("Castillo", "Sergio"),
    ("Carrizo", "Cecilia"),
    ("Gutierrez", "Alvaro"),
    ("Peralta", "Walter"),
)

_LEGACY_KEY_TO_PARTS: dict[str, tuple[str, str]] = {}
for _ap, _no in _RELEVADOR_PARTS:
    _LEGACY_KEY_TO_PARTS[normalize_catalog_key(f"{_ap}, {_no}")] = (_ap, _no)
    _LEGACY_KEY_TO_PARTS[normalize_catalog_key(f"{_no} {_ap}")] = (_ap, _no)
    _LEGACY_KEY_TO_PARTS[normalize_catalog_key(f"{_ap} {_no}")] = (_ap, _no)


def relevador_partes_desde_nombre(nombre: str) -> tuple[str, str]:
    """
    Resuelve apellido y nombre desde el valor persistido o variantes históricas.

    Si no hay match canónico, asume ``Apellido, Nombre`` si hay coma; si no, una sola parte.
    """
    raw = (nombre or "").strip()
    if not raw:
        return ("", "")
    hit = _LEGACY_KEY_TO_PARTS.get(normalize_catalog_key(raw))
    if hit:
        return hit
    if "," in raw:
        ap, _, rest = raw.partition(",")
        return ap.strip(), rest.strip()
    parts = raw.split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return raw, ""


def relevador_etiqueta_catalogo(nombre: str) -> str:
    """Formato ``Apellido, Nombre`` para listados y dropdowns."""
    ap, no = relevador_partes_desde_nombre(nombre)
    if ap and no:
        return f"{ap}, {no}"
    return ap or no or (nombre or "").strip()


def relevador_sort_key(nombre: str) -> tuple[str, str]:
    """Clave de orden alfabético apellido, nombre."""
    ap, no = relevador_partes_desde_nombre(nombre)
    return (ap.casefold(), no.casefold())


def relevador_nombres_equivalentes(a: str, b: str) -> bool:
    """True si dos variantes de nombre referencian al mismo relevador lógico."""
    return relevador_sort_key(a) == relevador_sort_key(b) and relevador_sort_key(a) != ("", "")
