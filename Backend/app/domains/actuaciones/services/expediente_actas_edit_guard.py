"""
Reglas de edición de notificación / comprobación desde el canal **Cargar actuación** (grilla).

Si una notificación ya tiene al menos un expediente asociado (historial de plazos), no debe
mutarse desde ese canal. Si una comprobación ya tiene expediente de envío (`oficio_id` NULL),
idem.

`aplicar_payload_actuacion` (p. ej. Completar trabajo) no usa estas validaciones; solo
`actualizar_actuacion`.
"""

from __future__ import annotations

from typing import Any, Dict

from app.database import db
from app.models import Actuaciones, Expediente


def notificacion_tiene_expediente_asociado(notificacion_id: int | None) -> bool:
    """
    True si existe al menos un expediente no borrado vinculado a la notificación.
    """
    if not notificacion_id:
        return False
    return (
        db.session.query(Expediente.id)
        .filter(
            Expediente.notificacion_id == notificacion_id,
            Expediente.deleted_at.is_(None),
        )
        .first()
        is not None
    )


def comprobacion_tiene_expediente_envio(comprobacion_id: int | None) -> bool:
    """
    True si existe expediente de envío de comprobación: misma regla que `expediente_envio_por_comprobacion`
    (comprobacion_id + oficio_id NULL), no soft-deleted.
    """
    if not comprobacion_id:
        return False
    return (
        Expediente.query.filter(
            Expediente.comprobacion_id == comprobacion_id,
            Expediente.oficio_id.is_(None),
            Expediente.deleted_at.is_(None),
        )
        .order_by(Expediente.id.asc())
        .first()
        is not None
    )


def notificacion_editable_desde_canal_actas(notificacion_id: int | None) -> bool:
    """Puede editarse la notificación desde la grilla de actuaciones."""
    return not notificacion_tiene_expediente_asociado(notificacion_id)


def comprobacion_editable_desde_canal_actas(comprobacion_id: int | None) -> bool:
    """Puede editarse la comprobación desde la grilla de actuaciones."""
    return not comprobacion_tiene_expediente_envio(comprobacion_id)


def assert_canal_actas_permite_payload_notificacion_comprobacion(
    act: Actuaciones, payload: Dict[str, Any]
) -> None:
    """
    Raises:
        ValueError: si el payload intenta mutar notificación/comprobación y el bloqueo aplica.
    """
    if payload.get("notificacion") is not None:
        if notificacion_tiene_expediente_asociado(act.notificacion_id):
            raise ValueError(
                "La notificación ya tiene expediente asociado y no puede editarse desde esta vista."
            )
    if payload.get("comprobacion") is not None:
        if comprobacion_tiene_expediente_envio(act.comprobacion_id):
            raise ValueError(
                "La comprobación ya tiene expediente asociado y no puede editarse desde esta vista."
            )
