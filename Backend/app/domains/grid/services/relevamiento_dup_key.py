from __future__ import annotations

import re
from typing import Any

_SPACE_RE = re.compile(r"\s+")


def _clean_str(v: Any) -> str:
    s = ("" if v is None else str(v)).strip()
    return s


def build_relevamiento_location_key(calle: str, numero: str) -> str:
    """
    Clave estable para comparar “misma ubicación” en grilla/lote (calle + número o texto de esquina).

    Usada para detectar duplicados en el lote cuando el domicilio no es ESQUINA (una fila por clave).
    Para esquinas no se usa para bloquear, pero se guarda por fila para limpiar el índice al editar.
    """
    c = _clean_str(calle).upper()
    c = _SPACE_RE.sub(" ", c)
    n = _clean_str(numero).upper()
    n = _SPACE_RE.sub(" ", n)
    return f"{c}|{n}"
