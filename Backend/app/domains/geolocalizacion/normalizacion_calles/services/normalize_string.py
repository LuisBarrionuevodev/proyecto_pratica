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

# Números en palabras (calles fechadas). Se aplican frases largas primero.
_NUMBER_PHRASES: tuple[tuple[str, str], ...] = (
    ("treinta y uno", "31"),
    ("treinta y tres", "33"),
    ("treinta y dos", "32"),
    ("treinta y cuatro", "34"),
    ("treinta y cinco", "35"),
    ("treinta y seis", "36"),
    ("treinta y siete", "37"),
    ("treinta y ocho", "38"),
    ("treinta y nueve", "39"),
    ("veinticuatro", "24"),
    ("veinticinco", "25"),
    ("veintiseis", "26"),
    ("veintisiete", "27"),
    ("veintiocho", "28"),
    ("veintinueve", "29"),
    ("veintitres", "23"),
    ("veintidos", "22"),
    ("veintiuno", "21"),
    ("catorce", "14"),
    ("trece", "13"),
    ("once", "11"),
    ("doce", "12"),
    ("diecinueve", "19"),
    ("dieciocho", "18"),
    ("diecisiete", "17"),
    ("dieciseis", "16"),
    ("diez", "10"),
    ("nueve", "9"),
    ("ocho", "8"),
    ("siete", "7"),
    ("seis", "6"),
    ("cinco", "5"),
    ("cuatro", "4"),
    ("tres", "3"),
    ("dos", "2"),
    ("uno", "1"),
    ("un", "1"),
)

_NUMBER_WORDS = {phrase: num for phrase, num in _NUMBER_PHRASES}

_DIGIT_TOKEN_RE = re.compile(r"^\d+$")


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


def expand_number_words(text: str) -> str:
    """
    Convierte números escritos en palabras a dígitos (calles fechadas).

    Ej.: ``nueve de julio`` → ``9 de julio``, ``veinticuatro de septiembre`` → ``24 de septiembre``.

    Parámetros:
        text: texto ya preprocesado o crudo.

    Retorno:
        Texto con números normalizados a dígitos.
    """
    s = preprocess_street_input(text)
    if not s:
        return ""
    for phrase, num in sorted(_NUMBER_PHRASES, key=lambda x: len(x[0]), reverse=True):
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b")
        s = pattern.sub(num, s)
    return s.strip()


def normalize_street(text: str) -> str:
    """
    Normaliza calle para matching (abreviaturas expandidas, números en palabra, sin tildes).
    """
    s = expand_number_words(text)
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


def _is_significant_token(token: str) -> bool:
    """Token relevante para matching: no stopword; incluye dígitos (9, 24)."""
    if not token or token in _STOPWORDS:
        return False
    if _DIGIT_TOKEN_RE.match(token):
        return True
    return len(token) > 1


def significant_tokens(text: str) -> list[str]:
    """
    Tokens significativos de una calle (sin stopwords; conserva números).

    Parámetros:
        text: nombre de calle crudo o canon_base.

    Retorno:
        Lista ordenada de tokens para matching.
    """
    base = street_base(text)
    if not base:
        base = normalize_street(text)
    tokens = base.split()
    return [t for t in tokens if _is_significant_token(t)]


def matching_token_set(text: str) -> frozenset[str]:
    """
    Conjunto de tokens para comparación exacta/contención (PR6A).

    Parámetros:
        text: texto de calle.

    Retorno:
        ``frozenset`` de tokens significativos.
    """
    return frozenset(significant_tokens(text))
