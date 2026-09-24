from __future__ import annotations

from app.database import db

from .update_service import _get_actuacion_or_404
from app.domains.actuaciones.cleanup.garbage_collector import (
    soft_delete_contribuyente_if_orphan,
    soft_delete_domicilio_if_orphan,
    soft_delete_orden_id_orphan,
    soft_delete_notificacion_if_orphan,
    soft_delete_comprobacion_if_orphan,
    soft_delete_oficio_if_orphan,
    soft_delete_expediente_if_orphan,
)
from app.models import Domicilio, Oficio, Expediente


def eliminar_actuacion(actuacion_id: int) -> None:
    """
    Elimina una `Actuaciones` por id.

    Mantiene el comportamiento histórico:
    - Si la actuación no existe -> `ValueError("Actuación no encontrada.")`.
    - Si existe, hace `db.session.delete(...)` + `db.session.commit()`.

    Args:
        actuacion_id: id de la actuación a eliminar.

    Returns:
        None

    Raises:
        ValueError: si la actuación no existe.
    """
    act = _get_actuacion_or_404(actuacion_id)
    old_domicilio_id = act.domicilio_id
    old_notificacion_id = act.notificacion_id
    old_comprobacion_id = act.comprobacion_id
    old_orden_trabajo_id = act.orden_trabajo_id

    # Snapshot de oficio/expediente ligados a comprobación (si existe)
    oficios_ids = []
    expedientes_ids = []
    if old_comprobacion_id:
        oficios_ids = [o.id for o in Oficio.query.filter_by(comprobacion_id=old_comprobacion_id).all()]
        expedientes_ids = [e.id for e in Expediente.query.filter_by(comprobacion_id=old_comprobacion_id).all()]

    # Snapshot de contribuyente (si hay domicilio)
    old_contribuyente_id = None
    if old_domicilio_id:
        dom = db.session.get(Domicilio, old_domicilio_id)
        if dom:
            old_contribuyente_id = dom.contribuyente_id

    db.session.delete(act)
    db.session.commit()

    # Garbage collector (solo tablas del último bloque)
    if old_domicilio_id:
        soft_delete_domicilio_if_orphan(old_domicilio_id)
    if old_contribuyente_id:
        soft_delete_contribuyente_if_orphan(old_contribuyente_id)
    if old_orden_trabajo_id:
        soft_delete_orden_id_orphan(old_orden_trabajo_id)
    if old_notificacion_id:
        soft_delete_notificacion_if_orphan(old_notificacion_id)
    if old_comprobacion_id:
        soft_delete_comprobacion_if_orphan(old_comprobacion_id)
    for oid in oficios_ids:
        soft_delete_oficio_if_orphan(oid)
    for eid in expedientes_ids:
        soft_delete_expediente_if_orphan(eid)

    db.session.commit()
