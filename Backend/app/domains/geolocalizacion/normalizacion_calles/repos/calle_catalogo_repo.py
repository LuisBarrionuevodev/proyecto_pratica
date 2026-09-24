from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import func

from app.models import CalleCatalogo


def get_by_key(nombre_key: str) -> Optional[CalleCatalogo]:
    """
    Busca una calle por key exacta (activa).
    """
    return CalleCatalogo.query.filter_by(nombre_key=nombre_key, activo=True).first()


def get_by_canon_base(canon_base: str) -> List[CalleCatalogo]:
    """
    Busca calles por canon_base exacto (activa).
    """
    return (
        CalleCatalogo.query.filter_by(canon_base=canon_base, activo=True)
        .all()
    )


def get_by_nombre_canonico(nombre_canonico: str) -> Optional[CalleCatalogo]:
    """
    Busca calle activa por nombre canónico (case-insensitive).
    """
    canon = (nombre_canonico or "").strip()
    if not canon:
        return None
    return (
        CalleCatalogo.query.filter(
            func.upper(CalleCatalogo.nombre_canonico) == canon.upper(),
            CalleCatalogo.activo.is_(True),
        )
        .first()
    )


def list_active_keys() -> List[Tuple[int, str, str, str]]:
    """
    Devuelve lista (id, canon_base, nombre_key, nombre_canonico) activa.
    """
    rows = (
        CalleCatalogo.query.with_entities(
            CalleCatalogo.id,
            CalleCatalogo.canon_base,
            CalleCatalogo.nombre_key,
            CalleCatalogo.nombre_canonico,
        )
        .filter(CalleCatalogo.activo.is_(True))
        .all()
    )
    return [(r[0], r[1], r[2], r[3]) for r in rows]


def search_catalogo(search: Optional[str], limit: int = 20) -> List[Tuple[int, str]]:
    """
    Busca calles activas por nombre canónico (like).
    """
    query = CalleCatalogo.query.filter(CalleCatalogo.activo.is_(True))
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(func.upper(CalleCatalogo.nombre_canonico).like(func.upper(like)))
    rows = (
        query.with_entities(CalleCatalogo.id, CalleCatalogo.nombre_canonico)
        .order_by(CalleCatalogo.nombre_canonico.asc())
        .limit(limit)
        .all()
    )
    return [(r[0], r[1]) for r in rows]
