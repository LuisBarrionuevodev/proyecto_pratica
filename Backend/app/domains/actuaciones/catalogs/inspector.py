from __future__ import annotations

from typing import List

from app.models import Inspector


def get_inspectores_o_falla(nombres: List[str]) -> List[Inspector]:
    """
    Resuelve Inspectores desde catálogo (lookup estricto por nombre).

    Reglas:
    - Se recorren los `nombres` en orden; los valores vacíos se ignoran.
    - Por cada nombre no vacío:
        - Se aplica `strip()`
        - Se busca `Inspector` por `nombre` exacto.
        - Si no existe -> `ValueError` (rechazo duro).
    - Devuelve una lista con los inspectores encontrados (mantiene el orden del input).

    Parámetros:
    - nombres: lista de strings con nombres de inspectores.

    Returns:
    - Lista de `Inspector` existentes.

    Raises:
    - ValueError: si algún nombre no vacío no existe en el catálogo.
    """
    encontrados: List[Inspector] = []

    for n in nombres:
        s = (n or "").strip()
        if not s:
            continue
        ins = Inspector.query.filter_by(nombre=s).first()
        if not ins:
            raise ValueError(f"Inspector no existe en catálogo: {s}")
        encontrados.append(ins)

    return encontrados
