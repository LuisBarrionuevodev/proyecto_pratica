"""Normalización técnica para reconciliar nombres de catálogo."""

from __future__ import annotations

import re
import unicodedata


def normalize_catalog_key(value: str) -> str:
    """
    Clave de comparación: trim, espacios colapsados, casefold.

    No altera el valor almacenado; solo identifica equivalencias técnicas.
    """
    text = (value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def normalize_ai_ci_identity(value: str) -> str:
    """
    Identidad compatible con columnas MySQL ``utf8mb4_0900_ai_ci``.

    Aplica trim, colapso de espacios, NFC, casefold y eliminación de marcas
    diacríticas (acentos). No realiza equivalencias semánticas amplias.
    """
    text = unicodedata.normalize("NFC", (value or "").strip())
    text = re.sub(r"\s+", " ", text)
    text = text.casefold()
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def normalize_catalog_display(value: str) -> str:
    """Trim y colapsa espacios para el valor canónico almacenado."""
    return re.sub(r"\s+", " ", (value or "").strip())
