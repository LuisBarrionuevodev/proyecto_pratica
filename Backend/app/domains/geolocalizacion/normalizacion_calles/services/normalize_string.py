"""
Normalización textual de calles para matching local (PR4).

Expansión de abreviaturas, títulos y limpieza previa al fuzzy/alias.
"""

from __future__ import annotations

import re
import unicodedata

_SPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[.,;:\-_/()\"']")

_VIA_TYPES = frozenset(
    {
        "calle",
        "avenida",
        "pasaje",
        "camino",
        "ruta",
        "boulevard",
        "diagonal",
        "autopista",
        "travesia",
    }
)

_TITLE_PREFIXES = frozenset(
    {
        "doctor",
        "doctora",
        "general",
        "profesor",
        "profesora",
        "ingeniero",
        "capitan",
        "teniente",
        "santo",
        "santa",
    }
)

_STOPWORDS = frozenset({"de", "del", "la", "las", "el", "los", "y", "e", "al", "a"})

_ABBREV_MAP = {
    "av": "avenida",
    "av.": "avenida",
    "avda": "avenida",
    "avd": "avenida",
    "aven": "avenida",
    "pje": "pasaje",
    "pje.": "pasaje",
    "pas": "pasaje",
    "pza": "plaza",
    "pl": "plaza",
    "diag": "diagonal",
    "bv": "boulevard",
    "blvd": "boulevard",
    "dr": "doctor",
    "dra": "doctora",
    "gral": "general",
    "gr": "general",
    "prof": "profesor",
    "ing": "ingeniero",
    "sgo": "santiago",
    "sta": "santa",
    "sto": "santo",
    "tte": "teniente",
    "cap": "capitan",
    "calle": "calle",
}

# Errores de tipeo / variantes frecuentes antes del tokenizado.
_TYPO_REPLACEMENTS = (
    (re.compile(r"\bmartin\b"), "martin"),
    (re.compile(r"\bestero\b"), "estero"),
)


def _strip_accents(text: str) -> str:
    s = unicodedata.normalize("NFKD", text)
    return "".join(c for c in s if not unicodedata.combining(c))


def slug_key(text: str) -> str:
    """
    Genera una key normalizada para matching.
    """
    s = preprocess_street_input(text)
    return s


def normalize_display(text: str) -> str:
    """
    Normaliza visualmente sin inventar mayúsculas.
    """
    s = (text or "").strip()
    s = _SPACE_RE.sub(" ", s)
    return s


def preprocess_street_input(text: str) -> str:
    """
    Limpia texto de entrada: minúsculas, sin tildes, puntuación y espacios.
    """
    s = (text or "").strip().lower()
    if not s:
        return ""
    s = _strip_accents(s)
    s = _PUNCT_RE.sub(" ", s)
    for pattern, repl in _TYPO_REPLACEMENTS:
        s = pattern.sub(repl, s)
    s = _SPACE_RE.sub(" ", s).strip()
    return s


def normalize_street(text: str) -> str:
    """
    Normaliza calle para matching (abreviaturas expandidas, sin tildes).
    """
    s = preprocess_street_input(text)
    if not s:
        return ""
    tokens = s.split(" ")
    tokens = [_ABBREV_MAP.get(t, t) for t in tokens]
    return " ".join(tokens)


def street_base(text: str) -> str:
    """
    Base de calle sin tipo de vía ni títulos honoríficos iniciales.
    """
    s = normalize_street(text)
    if not s:
        return ""
    tokens = s.split(" ")
    while tokens and tokens[0] in _VIA_TYPES:
        tokens = tokens[1:]
    while tokens and tokens[0] in _TITLE_PREFIXES:
        tokens = tokens[1:]
    return " ".join(tokens).strip()


def significant_tokens(text: str) -> list[str]:
    """
    Tokens significativos de una calle (sin stopwords ni tokens de 1 char).
    """
    base = street_base(text)
    if not base:
        base = preprocess_street_input(text)
    tokens = base.split()
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]
