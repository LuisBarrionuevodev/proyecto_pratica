from __future__ import annotations

from app.models import Motivo


def get_motivo_o_falla(nombre: str) -> Motivo:
    """
    Resuelve un Motivo desde el catálogo (lookup estricto).

    Reglas:
    - `nombre` se limpia con `strip()`.
    - Si queda vacío -> `ValueError`.
    - Si no existe un `Motivo.nombre` igual -> `ValueError`.

    Parámetros:
    - nombre: nombre del motivo (string) tal como llega del payload / grilla.

    Returns:
    - Instancia de `Motivo` existente en DB.

    Raises:
    - ValueError: si el nombre es vacío o no existe en el catálogo.
    """
    s = (nombre or "").strip()
    if not s:
        raise ValueError("Motivo inválido (vacío).")

    m = Motivo.query.filter_by(nombre=s).first()
    if not m:
        raise ValueError(f"Motivo no existe en catálogo: {s}")
    return m
