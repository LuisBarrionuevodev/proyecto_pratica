from __future__ import annotations

from typing import List, Optional

from app.models import Domicilio
from sqlalchemy import or_, and_


def get_domicilio(domicilio_id: int) -> Domicilio | None:
    """
    Obtiene un domicilio por id.
    """
    return Domicilio.query.get(domicilio_id)


def list_pendientes(limit: int, only: Optional[str] = None) -> List[Domicilio]:
    """
    Lista domicilios con normalización pendiente o con error.
    """
    calle_pendiente = Domicilio.calle_norm_status.in_(["PENDIENTE", "NO_MATCH", "REVIEW"])
    esquina_pendiente = Domicilio.esquina_norm_status.in_(
        ["PENDIENTE", "NO_MATCH", "REVIEW"]
    )

    query = Domicilio.query.filter(Domicilio.calle.isnot(None))
    if only == "calle":
        query = query.filter(calle_pendiente)
    elif only == "esquina":
        query = query.filter(esquina_pendiente)
    else:
        query = query.filter(or_(calle_pendiente, esquina_pendiente))

    return query.limit(limit).all()
