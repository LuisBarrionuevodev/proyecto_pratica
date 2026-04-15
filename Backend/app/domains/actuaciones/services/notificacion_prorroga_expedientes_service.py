"""
Consulta documental de expedientes de prórroga (rama NOTIFICACION).

Los días solicitados en cada alta de expediente **no** se guardan por fila en ``expediente``;
solo existe el acumulado en ``Notificacion.prorroga_dias`` (ver ``aplicar_prorroga_notificacion``).
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.database import db
from app.models import Actuaciones, Expediente, Notificacion


def _expediente_prorroga_to_item(ex: Expediente) -> Dict[str, Any]:
    return {
        "id": ex.id,
        "numero_expediente": ex.numero_expediente,
        "anio": ex.anio,
        "fecha_expediente": ex.fecha_expediente.isoformat() if ex.fecha_expediente else None,
        "created_at": ex.created_at.isoformat() if ex.created_at else None,
        "tipo_expediente": ex.tipo_expediente,
        # Reservado: hoy el modelo no persiste el delta por fila; migración futura podría llenarlo.
        "prorroga_dias_solicitada": None,
    }


def list_notificacion_prorroga_expedientes_for_actuacion(actuacion_id: int) -> Dict[str, Any]:
    """
    Lista expedientes ``PRORROGA_NOTIFICACION`` de la notificación vinculada a la actuación,
    más métricas consolidadas de plazo en ``Notificacion``.

    Qué hace:
    - Resuelve ``Actuaciones`` por id.
    - Exige ``notificacion_id`` (rama con acta de notificación).
    - Ordena expedientes por ``id`` ascendente (orden de alta / documental).

    Parámetros:
        actuacion_id: PK de la actuación (misma clave que usa la bandeja / modal).

    Retorno:
        dict serializable con ``actuacion_id``, ``notificacion_id``, ``plazos_otorgados``,
        ``consolidado`` (plazo/prórroga/fechas de la notificación) e ``items`` (filas expediente).

    Errores:
        LookupError: actuación inexistente.
        ValueError: actuación sin ``notificacion_id``.
    """
    act = db.session.get(Actuaciones, actuacion_id)
    if act is None:
        raise LookupError("Actuación no encontrada")
    if act.notificacion_id is None:
        raise ValueError("La actuación no tiene notificación asociada")

    noti = db.session.get(Notificacion, int(act.notificacion_id))
    if noti is None:
        raise ValueError("Notificación no encontrada para la actuación")

    expedientes: List[Expediente] = (
        Expediente.query.filter_by(notificacion_id=noti.id)
        .filter(Expediente.tipo_expediente == "PRORROGA_NOTIFICACION")
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.asc())
        .all()
    )

    items = [_expediente_prorroga_to_item(ex) for ex in expedientes]

    consolidado: Dict[str, Any] = {
        "plazo_dias": noti.plazo_dias,
        "prorroga_dias": noti.prorroga_dias,
        "fecha_notificacion": noti.fecha_notificacion.isoformat() if noti.fecha_notificacion else None,
        "fecha_vencimiento": noti.fecha_vencimiento.isoformat() if noti.fecha_vencimiento else None,
    }

    return {
        "actuacion_id": act.id,
        "notificacion_id": noti.id,
        "plazos_otorgados": len(items),
        "consolidado": consolidado,
        "items": items,
    }
