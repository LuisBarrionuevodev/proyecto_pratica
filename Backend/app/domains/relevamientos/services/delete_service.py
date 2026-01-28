from __future__ import annotations

from app.database import db
from app.models import Relevamiento


def eliminar_relevamiento(relevamiento_id: int) -> None:
    """
    Elimina un Relevamiento por id.

    Args:
        relevamiento_id: id del relevamiento.

    Raises:
        ValueError: si no existe.
    """
    rel = Relevamiento.query.get(relevamiento_id)
    if not rel:
        raise ValueError("Relevamiento no encontrado.")
    db.session.delete(rel)
    db.session.commit()
