from __future__ import annotations

from datetime import datetime

from app.database import db
from app.models import Relevamiento
from app.domains.actuaciones.cleanup.garbage_collector import (
    soft_delete_domicilio_if_orphan,
)
from app.domains.rutas_trabajo.services.anular_iniciador_por_origen_service import (
    anular_iniciadores_por_origen,
)


def eliminar_relevamiento(relevamiento_id: int) -> None:
    """
    Elimina un Relevamiento por id.

    Args:
        relevamiento_id: id del relevamiento.

    Raises:
        ValueError: si no existe.
        IniciadorOrigenEnUsoError: si el iniciador ya fue utilizado operativamente.
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

    anular_iniciadores_por_origen(
        tipo_origen="RELEVAMIENTO",
        origen_id=int(relevamiento_id),
        cerrado_motivo="SOFT_DELETE_RELEVAMIENTO",
    )

    old_domicilio_id = rel.domicilio_id
    rel.deleted_at = datetime.utcnow()
    db.session.add(rel)
    db.session.commit()

    if old_domicilio_id is not None:
        soft_delete_domicilio_if_orphan(old_domicilio_id)
        db.session.commit()
