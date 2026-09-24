from __future__ import annotations

"""
Utilidades para normalizar filas del grid.

- Glide puede enviar columnas con espacios o headers humanos.
- Internamente validamos con keys snake_case.
"""

from typing import Any, Dict


def _collapse_spaces(s: str) -> str:
    """Hace strip y colapsa múltiples espacios a uno solo."""
    return " ".join(s.strip().split())


def normalize_row_keys(row_raw: Dict[str, Any], column_map: Dict[str, str]) -> Dict[str, Any]:
    """
    Normaliza keys del row raw usando un COLUMN_MAP (Glide -> interno).

    Reglas:
    - Hace strip() de keys y colapsa espacios múltiples para comparar.
    - Solo mapea las keys presentes.
    - Conserva keys no mapeadas tal cual (para no romper otros dominios/campos).
    - Para keys mapeadas, emite la key interna y NO conserva la original.
    """
    out: Dict[str, Any] = {}
    for k, v in (row_raw or {}).items():
        key_norm = _collapse_spaces(str(k))
        internal_key = column_map.get(key_norm)
        if internal_key:
            out[internal_key] = v
        else:
            out[k] = v
    return out


def reverse_map_errors(errors_internal: Dict[str, str], column_map: Dict[str, str]) -> Dict[str, str]:
    """
    Convierte errores internos (snake_case) a nombres de columna de Glide.

    - Si no encuentra mapping, deja la key tal cual.
    - Preserva keys especiales (ej: "_row", "detail").
    """
    inv = {internal: glide for glide, internal in column_map.items()}
    out: Dict[str, str] = {}
    for k, msg in (errors_internal or {}).items():
        if k in ("_row", "detail"):
            out[k] = msg
            continue
        out[inv.get(k, k)] = msg
    return out

