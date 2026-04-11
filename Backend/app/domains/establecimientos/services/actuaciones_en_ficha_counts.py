"""
Conteos de actuaciones agrupadas por ``establecimiento_operativo_id`` (para presenter sin N+1).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import func

from app.database import db
from app.models import Actuaciones


def count_actuaciones_por_establecimiento_operativo_ids(eo_ids: list[int]) -> dict[int, int]:
    """
    Devuelve cuántas filas en ``actuaciones`` tienen cada ``establecimiento_operativo_id``.

    Una consulta agrupada; ids vacíos retornan dict vacío.
    """
    if not eo_ids:
        return {}
    rows = (
        db.session.query(
            Actuaciones.establecimiento_operativo_id,
            func.count(Actuaciones.id),
        )
        .filter(Actuaciones.establecimiento_operativo_id.in_(eo_ids))
        .group_by(Actuaciones.establecimiento_operativo_id)
        .all()
    )
    return {int(eo_id): int(n) for eo_id, n in rows if eo_id is not None}


def build_counts_by_eo_from_actuaciones(acts: Iterable[Any]) -> dict[int, int]:
    """
    Extrae ids únicos de ficha desde una lista de ``Actuaciones`` y obtiene conteos en batch.
    """
    ids: set[int] = set()
    for a in acts:
        eid = getattr(a, "establecimiento_operativo_id", None)
        if eid is not None:
            ids.add(int(eid))
    return count_actuaciones_por_establecimiento_operativo_ids(sorted(ids))
