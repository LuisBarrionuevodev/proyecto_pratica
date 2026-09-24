from __future__ import annotations

import re
from typing import Literal


NumeroTipo = Literal["NUMERO", "ESQUINA", "OTRO"]

_ONLY_DIGITS_RE = re.compile(r"^\d+(\s+\d+)*$")
_HAS_LETTERS_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]")
_HAS_DIGITS_RE = re.compile(r"\d")
_OTRO_PATTERNS = [
    re.compile(r"^S/?N(º|°)?$", re.IGNORECASE),
    re.compile(r"^SN$", re.IGNORECASE),
    re.compile(r"^SIN\s*(NUMERO|NRO)$", re.IGNORECASE),
    re.compile(r"^S/?NRO$", re.IGNORECASE),
    re.compile(r"^KM\s*\d+(\.\d+)?$", re.IGNORECASE),
]


def detect_numero_o_esquina(valor: str) -> NumeroTipo:
    """
    Detecta si un valor de "Número" es NUMERO, ESQUINA u OTRO.

    Reglas:
    - Solo dígitos (o dígitos con espacios) -> NUMERO
    - Letras sin dígitos -> ESQUINA
    - Patrones especiales (S/N, KM 3, etc.) -> OTRO
    - Letras + dígitos -> OTRO
    """
    s = (valor or "").strip()
    if not s:
        return "OTRO"

    s_norm = " ".join(s.split())

    if _ONLY_DIGITS_RE.fullmatch(s_norm):
        return "NUMERO"

    for pattern in _OTRO_PATTERNS:
        if pattern.fullmatch(s_norm):
            return "OTRO"

    has_letters = bool(_HAS_LETTERS_RE.search(s_norm))
    has_digits = bool(_HAS_DIGITS_RE.search(s_norm))

    if has_letters and not has_digits and len(s_norm) > 2:
        return "ESQUINA"

    return "OTRO"
