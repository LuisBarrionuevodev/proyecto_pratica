"""
Catálogo liviano de rubros desde DB (STAB-8).

Fuente única para grid y /catalogos/rubros.
"""

from __future__ import annotations

from typing import Any

from app.models import Rubro

_DEFAULT_LIMIT = 500


def listar_rubros_catalogo(
    *,
    q: str | None = None,
    limit: int = _DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """
    Lista rubros ordenados por nombre.

    Parámetros:
        q: filtro opcional por nombre (ILIKE parcial).
        limit: máximo de filas (default 500).

    Retorno:
        Lista de dicts ``{ id, nombre, activo }``.
        ``activo`` es siempre True hasta migración de columna ``activo`` en ``rubro``.
    """
    query = Rubro.query.order_by(Rubro.nombre.asc())
    term = (q or "").strip()
    if term:
        query = query.filter(Rubro.nombre.ilike(f"%{term}%"))
    lim = max(1, min(int(limit), 500))
    rows = query.limit(lim).all()
    return [
        {
            "id": int(r.id),
            "nombre": r.nombre,
            "activo": True,
        }
        for r in rows
    ]
