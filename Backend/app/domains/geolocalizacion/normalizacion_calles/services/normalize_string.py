from __future__ import annotations

import re
import unicodedata


_SPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[.,;:\-_/]")
_VIA_TYPES = {
    "calle",
    "avenida",
    "pasaje",
    "camino",
    "ruta",
    "boulevard",
    "diagonal",
    "autopista",
    "travesia",
    "travesía",
}
_ABBREV_MAP = {
    "av": "avenida",
    "avda": "avenida",
    "avd": "avenida",
    "pje": "pasaje",
    "pje.": "pasaje",
    "pza": "plaza",
    "diag": "diagonal",
}


def slug_key(text: str) -> str:
    """
    Genera una key normalizada para matching.
    """
    s = (text or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = _PUNCT_RE.sub(" ", s)
    s = _SPACE_RE.sub(" ", s).strip()
    return s


def normalize_display(text: str) -> str:
    """
    Normaliza visualmente sin inventar mayúsculas.
    """
    s = (text or "").strip()
    s = _SPACE_RE.sub(" ", s)
    return s


def normalize_street(text: str) -> str:
    """
    Normaliza calle para matching (minusculas, sin tildes, abreviaturas).
    """
    s = (text or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = _PUNCT_RE.sub(" ", s)
    s = _SPACE_RE.sub(" ", s).strip()
    if not s:
        return ""
    tokens = s.split(" ")
    tokens = [_ABBREV_MAP.get(t, t) for t in tokens]
    return " ".join(tokens)


def street_base(text: str) -> str:
    """
    Devuelve la base de la calle sin tipo de vía inicial.
    """
    s = normalize_street(text)
    if not s:
        return ""
    tokens = s.split(" ")
    if tokens and tokens[0] in _VIA_TYPES:
        tokens = tokens[1:]
    return " ".join(tokens).strip()
