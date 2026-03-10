from __future__ import annotations

from typing import Any, Dict, Tuple

from app.database import db
from app.models import Actuaciones, Expediente, Notificacion
from app.utils.actas import acta_6
from app.domains.actuaciones.services.notificacion_timing_service import aplicar_prorroga_notificacion


def infer_source_type_from_actuacion(act: Actuaciones) -> str:
    """
    Infiere el `source_type` para flujo de expediente a partir del estado DB.

    Reglas:
    - Si hay comprobación y notificación, domina COMPROBACION.
    - Si solo hay comprobación, COMPROBACION.
    - Si solo hay notificación, NOTIFICACION.
    - Si no hay ninguna, UNKNOWN.
    """
    if act.comprobacion_id is not None:
        return "COMPROBACION"
    if act.notificacion_id is not None:
        return "NOTIFICACION"
    return "UNKNOWN"


def _parse_expediente_payload(data: Dict[str, Any]) -> Tuple[str, str]:
    """
    Valida y normaliza `expediente_numero`/`expediente_anio`.

    Raises:
        ValueError: si faltan campos requeridos o son inválidos.
    """
    numero = acta_6(data.get("expediente_numero"))
    anio = data.get("expediente_anio")
    if not numero or anio is None:
        raise ValueError("expediente_numero y expediente_anio son obligatorios")

    anio_str = str(anio).strip()
    if len(anio_str) != 4 or not anio_str.isdigit():
        raise ValueError("expediente_anio debe tener 4 dígitos")
    return numero, anio_str


def _parse_prorroga_payload(data: Dict[str, Any]) -> int:
    """
    Valida prorroga_dias para rama NOTIFICACION.
    """
    value = data.get("prorroga_dias")
    if value is None:
        raise ValueError("prorroga_dias es obligatorio para NOTIFICACION")
    try:
        parsed = int(value)
    except Exception as exc:
        raise ValueError("prorroga_dias debe ser un entero") from exc
    if parsed < 0:
        raise ValueError("prorroga_dias debe ser mayor o igual a 0")
    return parsed


def complete_expediente_from_actuacion(
    actuacion_id: int,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Completa expediente para una actuación ramificando por `source_type` inferido.

    Retorno:
        dict con `actuacion`, `expediente`, `source_type`, `next_state_hint`.

    Errores:
        ValueError: 400 por payload inválido o actuación sin origen válido.
        LookupError: 404 cuando la actuación no existe.
        RuntimeError: 409 por conflictos de unicidad/consistencia.
    """
    act = Actuaciones.query.get(actuacion_id)
    if not act:
        raise LookupError("Actuación no encontrada")

    source_type = infer_source_type_from_actuacion(act)
    if source_type == "UNKNOWN":
        raise ValueError("La actuación no tiene acta de notificación ni de comprobación")

    provided_source_type = data.get("source_type")
    if provided_source_type:
        provided = str(provided_source_type).strip().upper()
        if provided != source_type:
            raise RuntimeError("source_type no coincide con el estado real de la actuación")

    numero, anio_str = _parse_expediente_payload(data)

    if source_type == "COMPROBACION":
        if "prorroga_dias" in data:
            raise ValueError("prorroga_dias no aplica para COMPROBACION")
        existente = Expediente.query.filter_by(comprobacion_id=act.comprobacion_id).first()
        if existente:
            raise RuntimeError("Ya existe un expediente vinculado a esta comprobación")
    else:
        prorroga_dias = _parse_prorroga_payload(data)
        if act.notificacion_id is None:
            raise ValueError("La actuación no tiene notificación para aplicar prórroga")
        noti = db.session.get(Notificacion, act.notificacion_id)
        if not noti:
            raise ValueError("No se encontró la notificación asociada a la actuación")
        existente = Expediente.query.filter_by(notificacion_id=act.notificacion_id).first()
        if existente:
            raise RuntimeError("Ya existe un expediente vinculado a esta notificación")
        aplicar_prorroga_notificacion(noti, prorroga_dias)
        db.session.add(noti)

    dup = Expediente.query.filter_by(numero_expediente=numero, anio=anio_str).first()
    if dup:
        raise RuntimeError("Ese expediente ya existe")

    ex = Expediente(
        numero_expediente=numero,
        anio=anio_str,
        comprobacion_id=act.comprobacion_id if source_type == "COMPROBACION" else None,
        notificacion_id=act.notificacion_id if source_type == "NOTIFICACION" else None,
        oficio_id=None,
    )

    db.session.add(ex)
    db.session.commit()

    next_state_hint = (
        "ESPERANDO_OFICIO" if source_type == "COMPROBACION" else "PENDIENTE_REINSPECCION"
    )

    return {
        "actuacion": act,
        "expediente": ex,
        "source_type": source_type,
        "next_state_hint": next_state_hint,
        "reinspeccion_due_date": (
            act.notificacion.fecha_vencimiento.isoformat()
            if source_type == "NOTIFICACION"
            and act.notificacion
            and act.notificacion.fecha_vencimiento
            else None
        ),
        "plazo_dias": (
            act.notificacion.plazo_dias
            if source_type == "NOTIFICACION" and act.notificacion
            else None
        ),
        "prorroga_dias": (
            act.notificacion.prorroga_dias
            if source_type == "NOTIFICACION" and act.notificacion
            else None
        ),
    }
