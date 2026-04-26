from __future__ import annotations

import re
from typing import Any

_SPACE_RE = re.compile(r"\s+")


def _clean_str(v: Any) -> str:
    s = ("" if v is None else str(v)).strip()
    return s


def build_relevamiento_location_key(calle: str, numero: str) -> str:
    """
    Clave estable para “misma ubicación” (calle + número / texto de esquina).

    Usada en la regla de duplicados del lote: la misma ubicación no puede
    aparecer con dos fechas distintas; sí puede repetirse la misma fecha
    (varios negocios en la misma esquina el mismo día).
    """
    c = _clean_str(calle).upper()
    c = _SPACE_RE.sub(" ", c)
    n = _clean_str(numero).upper()
    n = _SPACE_RE.sub(" ", n)
    return f"{c}|{n}"
