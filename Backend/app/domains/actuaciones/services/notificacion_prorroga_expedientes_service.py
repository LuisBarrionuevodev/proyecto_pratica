"""
Consulta de expedientes de prórroga (rama NOTIFICACION) y estado de plazo/vencimiento.

Cada fila ``PRORROGA_NOTIFICACION`` persiste ``prorroga_dias_otorgados``; el total en
``Notificacion.prorroga_dias`` debe coincidir con la suma de esas filas (recalculado al editar).
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.database import db
from app.models import Actuaciones, Expediente, Notificacion

from app.domains.actuaciones.services.notificacion_plazo_expediente_edit_service import (
    evaluar_expediente_prorroga_permisos,
    evaluar_notificacion_edicion_permisos,
)


def _expediente_prorroga_to_item(ex: Expediente, *, notificacion_id: int) -> Dict[str, Any]:
    per = evaluar_expediente_prorroga_permisos(notificacion_id, int(ex.id))
    motivos = per.get("motivos_bloqueo") or []
    return {
        "id": ex.id,
        "numero_expediente": ex.numero_expediente,
        "anio": ex.anio,
        "fecha_expediente": ex.fecha_expediente.isoformat() if ex.fecha_expediente else None,
        "created_at": ex.created_at.isoformat() if ex.created_at else None,
        "tipo_expediente": ex.tipo_expediente,
        "plazo_otorgado": ex.prorroga_dias_otorgados,
        "puede_editar": bool(per.get("puede_editar")),
        "puede_eliminar": bool(per.get("puede_eliminar")),
        "es_ultimo_expediente_activo": bool(per.get("es_ultimo_expediente_activo")),
        "motivo_bloqueo": motivos[0] if motivos else None,
    }


def list_notificacion_prorroga_expedientes_for_actuacion(actuacion_id: int) -> Dict[str, Any]:
    """
    Lista expedientes ``PRORROGA_NOTIFICACION`` de la notificación vinculada a la actuación,
    más métricas de plazo en ``Notificacion``.

    Parámetros:
        actuacion_id: PK de la actuación (misma clave que usa la bandeja / modal).

    Retorno:
        dict serializable con ``actuacion_id``, ``notificacion_id``, ``plazos_otorgados``,
        ``plazo_notificacion`` (plazo legal, prórroga total, fechas) e ``items`` (filas expediente).

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

    items = [_expediente_prorroga_to_item(ex, notificacion_id=int(noti.id)) for ex in expedientes]

    plazo_notificacion: Dict[str, Any] = {
        "plazo_legal_dias": noti.plazo_dias,
        "prorroga_total_dias": noti.prorroga_dias,
        "fecha_notificacion": noti.fecha_notificacion.isoformat() if noti.fecha_notificacion else None,
        "fecha_vencimiento": noti.fecha_vencimiento.isoformat() if noti.fecha_vencimiento else None,
    }

    return {
        "actuacion_id": act.id,
        "notificacion_id": noti.id,
        "plazos_otorgados": len(items),
        "plazo_notificacion": plazo_notificacion,
        "items": items,
        "edicion": evaluar_notificacion_edicion_permisos(act),
    }
