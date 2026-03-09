from __future__ import annotations

from datetime import datetime

from app.database import db
from app.models import Relevamiento
from app.domains.actuaciones.cleanup.garbage_collector import (
    soft_delete_domicilio_if_orphan,
)


def eliminar_relevamiento(relevamiento_id: int) -> None:
    """
    Elimina un Relevamiento por id.

    Args:
        relevamiento_id: id del relevamiento.

    Raises:
        ValueError: si no existe.
    """
    rel = (
        Relevamiento.query.filter(
            Relevamiento.id == relevamiento_id,
            Relevamiento.deleted_at.is_(None),
        )
        .limit(1)
        .first()
    )
    if not rel:
        raise ValueError("Relevamiento no encontrado.")

    old_domicilio_id = rel.domicilio_id
    rel.deleted_at = datetime.utcnow()
    db.session.add(rel)
    db.session.commit()

    if old_domicilio_id is not None:
        soft_delete_domicilio_if_orphan(old_domicilio_id)
        db.session.commit()
