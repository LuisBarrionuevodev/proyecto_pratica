"""Normalización de `IniciadorRuta.estado_iniciador` para comparaciones y serialización."""

from __future__ import annotations

from typing import Any


def normalize_estado_iniciador(value: Any) -> str | None:
    """
    Convierte el valor ORM/Enum/string de `estado_iniciador` a string canónico (ej. ``PENDIENTE``).

    Evita fallos de comparación estricta cuando el runtime devuelve Enum u otro tipo distinto de ``str``.

    Parámetros:
        value: valor leído de columna o relación SQLAlchemy.

    Retorno:
        String del estado o ``None`` si no hay valor utilizable.
    """
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return s or None
    inner = getattr(value, "value", value)
    if isinstance(inner, str):
        s = inner.strip()
        return s or None
    if inner is not None:
        return str(inner).strip() or None
    return None


def es_estado_iniciador_pendiente(value: Any) -> bool:
    """
    Indica si el iniciador está en ``PENDIENTE`` (bandejas operativas editables).

    Parámetros:
        value: valor de ``estado_iniciador`` tal como viene del ORM.

    Retorno:
        ``True`` solo si el estado normalizado es ``PENDIENTE``.
    """
    return normalize_estado_iniciador(value) == "PENDIENTE"
