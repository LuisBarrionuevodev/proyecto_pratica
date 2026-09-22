"""
Declaración documental: comprobación sin expediente de envío disponible.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import expediente_envio_por_comprobacion
from app.domains.rutas_trabajo.services.auth_service import resolve_actor_user_id
from app.models import Actuaciones, Comprobacion


def declarar_sin_expediente_envio(
    actuacion_id: int,
    *,
    actor_user_id: int | None = None,
) -> Dict[str, Any]:
    """
    Marca la comprobación como sin expediente de envío documental disponible.

    Parámetros:
        actuacion_id: actuación con comprobación en bandeja pendiente expediente.
        actor_user_id: usuario autenticado (auditoría).

    Retorno:
        dict con actuación, comprobación y flag de idempotencia.

    Errores:
        LookupError: actuación inexistente.
        ValueError: sin comprobación, expediente ya cargado, o comprobación borrada.
    """
    uid = resolve_actor_user_id(actor_user_id)
    act = db.session.get(Actuaciones, actuacion_id)
    if act is None:
        raise LookupError("Actuación no encontrada")
    if act.comprobacion_id is None:
        raise ValueError("La actuación no tiene comprobación asociada")

    comp = db.session.get(Comprobacion, int(act.comprobacion_id))
    if comp is None or comp.deleted_at is not None:
        raise ValueError("Comprobación no disponible")

    if expediente_envio_por_comprobacion(int(comp.id)):
        raise ValueError("Ya existe un expediente de envío activo para esta comprobación")

    if comp.sin_expediente_envio:
        return {
            "actuacion": act,
            "comprobacion": comp,
            "idempotent": True,
        }

    now = datetime.now(timezone.utc)
    comp.sin_expediente_envio = True
    comp.sin_expediente_envio_declarado_at = now
    comp.sin_expediente_envio_declarado_by_user_id = uid
    db.session.add(comp)
    db.session.commit()

    return {
        "actuacion": act,
        "comprobacion": comp,
        "idempotent": False,
    }
