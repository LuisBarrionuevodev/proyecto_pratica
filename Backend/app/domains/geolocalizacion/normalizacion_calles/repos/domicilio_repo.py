from __future__ import annotations

from typing import List

from app.models import Domicilio


def get_domicilio(domicilio_id: int) -> Domicilio | None:
    """
    Obtiene un domicilio por id.
    """
    return Domicilio.query.get(domicilio_id)


def list_pendientes(limit: int) -> List[Domicilio]:
    """
    Lista domicilios con normalización pendiente o con error.
    """
    return (
        Domicilio.query.filter(
            Domicilio.calle.isnot(None),
            Domicilio.calle_norm_status.in_(["PENDIENTE", "NO_MATCH", "REVIEW"]),
        )
        .limit(limit)
        .all()
    )
