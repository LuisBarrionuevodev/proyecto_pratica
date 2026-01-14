from __future__ import annotations

from typing import Optional

from app.models import Rubro


def get_rubro_o_falla(nombre: Optional[str]) -> Optional[Rubro]:
    """
    Resuelve un Rubro desde el catálogo (lookup estricto).

    Reglas:
    - Si `nombre` es `None` o vacío -> devuelve `None`.
    - Si `nombre` viene con espacios extra, se normaliza (trim + colapsa espacios internos).
    - Si `nombre` viene y NO existe en catálogo -> levanta `ValueError`.

    Parámetros:
    - nombre: nombre del rubro (string) tal como llega del payload.

    Returns:
    - `Rubro` si existe, o `None` si no se envió rubro.

    Raises:
    - ValueError: si se envió un nombre no vacío pero no existe en la tabla `Rubro`.
    """
    if nombre is None:
        return None

    s = str(nombre).strip()
    if not s:
        return None

    s = " ".join(s.split())
    rubro = Rubro.query.filter_by(nombre=s).first()
    if not rubro:
        raise ValueError(f"Rubro no existe en catálogo: {s}")
    return rubro
