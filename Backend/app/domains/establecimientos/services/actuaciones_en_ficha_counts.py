"""
Conteos de actuaciones por identidad lógica de ficha (FIX.7).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    count_actuaciones_identidad_logica,
)
from app.models import EstablecimientoOperativo


def count_actuaciones_por_establecimiento_operativo_ids(eo_ids: list[int]) -> dict[int, int]:
    """
    Devuelve cuántas actuaciones pertenecen a la identidad lógica de cada ficha canónica.

    Una consulta por ficha; ids vacíos retornan dict vacío.
    """
    if not eo_ids:
        return {}
    out: dict[int, int] = {}
    for eid in eo_ids:
        eo = (
            EstablecimientoOperativo.query.filter_by(id=int(eid))
            .options(joinedload(EstablecimientoOperativo.domicilio))
            .first()
        )
        if eo is None or eo.domicilio is None:
            out[int(eid)] = 0
            continue
        out[int(eid)] = count_actuaciones_identidad_logica(eo.domicilio)
    return out


def build_counts_by_eo_from_actuaciones(acts: Iterable[Any]) -> dict[int, int]:
    """
    Extrae ids únicos de ficha desde una lista de ``Actuaciones`` y obtiene conteos lógicos.
    """
    ids: set[int] = set()
    for a in acts:
        eid = getattr(a, "establecimiento_operativo_id", None)
        if eid is not None:
            ids.add(int(eid))
    return count_actuaciones_por_establecimiento_operativo_ids(sorted(ids))
