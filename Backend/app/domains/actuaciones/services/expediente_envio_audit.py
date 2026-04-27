"""
Consultas de auditoría para expedientes de **envío de comprobación** (`oficio_id` NULL).

Sirven para detectar datos legados (más de un expediente por comprobación) sin mutar BD.
"""

from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import func

from app.database import db
from app.models import Expediente


def fetch_comprobaciones_con_multiples_expedientes_envio() -> List[Tuple[int, int]]:
    """
    Lista pares ``(comprobacion_id, cantidad)`` donde hay más de un expediente activo
    con ``comprobacion_id`` set y ``oficio_id`` NULL (canal envío / no respuesta oficio).

    Returns:
        Lista ordenada por ``comprobacion_id`` ascendente.

    Nota:
        No filtra por ``tipo_expediente``; el conteo refleja todas las filas del criterio
        espacial (útil para revisión manual).
    """
    rows = (
        db.session.query(Expediente.comprobacion_id, func.count(Expediente.id).label("cnt"))
        .filter(
            Expediente.comprobacion_id.isnot(None),
            Expediente.oficio_id.is_(None),
            Expediente.deleted_at.is_(None),
        )
        .group_by(Expediente.comprobacion_id)
        .having(func.count(Expediente.id) > 1)
        .order_by(Expediente.comprobacion_id.asc())
        .all()
    )
    return [(int(r.comprobacion_id), int(r.cnt)) for r in rows]


def fetch_expedientes_envio_por_comprobacion(comprobacion_id: int) -> List[Expediente]:
    """
    Todos los expedientes de envío (``oficio_id`` NULL, no borrados) para una comprobación,
    ordenados por ``id`` ascendente (misma regla que el presenter).
    """
    return (
        Expediente.query.filter_by(comprobacion_id=comprobacion_id, oficio_id=None)
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.asc())
        .all()
    )
