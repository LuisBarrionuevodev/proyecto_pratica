"""Normalización de DNI/CUIT para búsquedas de historial (solo lectura)."""

from __future__ import annotations

import re


def normalizar_documento(documento: str | None) -> str:
    """
    Quita espacios, puntos y guiones de un documento para comparación.

    Parámetros:
        documento: valor ingresado (ej. ``20-33344455-5``, ``33.344.455``).

    Retorno:
        Cadena alfanumérica sin separadores; vacía si no hay entrada.
    """
    if documento is None:
        return ""
    return re.sub(r"[\s.\-]", "", str(documento).strip())
