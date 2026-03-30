from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Expediente, Oficio
from app.utils.actas import acta_6


def _expediente_label(numero: str, anio_str: str) -> str:
    return f"{numero}/{anio_str}"


def attach_expediente(
    data: Optional[Dict[str, Any]],
    comprobacion_id: Optional[int],
    oficio_id: Optional[int],
) -> Optional[Expediente]:
    """
    Resuelve (get o create) un `Expediente` según **contexto explícito** (no hay expediente “genérico”).

    Identificación: `(numero_expediente, anio)` (`anio` como string en DB).

    Modos:
    - **`oficio_id` None — expediente de comprobación (envío):** fila sin oficio; debe alinearse con
      la comprobación del contexto. No se mezcla con el expediente de respuesta de oficio.
    - **`oficio_id` set — expediente de respuesta de oficio:** misma clave debe pertenecer al mismo
      oficio; se valida coherencia con `comprobacion_id` del oficio.

    Ante conflicto de contexto: `ValueError` claro; **sin** reasignación silenciosa de FK.

    Nota: los canales CargarActuacion / CompletarTrabajo no envían este attach; quedan rutas
    especializadas u orquestación interna (p. ej. oficio + respuesta).

    Args:
        data: `numero`, `anio` obligatorios.
        comprobacion_id: comprobación del contexto (obligatoria si hay `data`).
        oficio_id: `None` = expediente de envío (comprobación); no `None` = expediente del oficio.

    Returns:
        `Expediente` o `None` si no hay `data`.

    Raises:
        ValueError: validación o conflicto de contexto.
    """
    if not data:
        return None

    if comprobacion_id is None:
        raise ValueError("Para cargar un expediente se requiere una comprobación de contexto.")

    numero = acta_6(data.get("numero"))
    anio = data.get("anio")

    if not numero or anio is None:
        raise ValueError("Si cargás expediente, número y año son obligatorios.")

    anio_str = str(anio)
    label = _expediente_label(numero, anio_str)

    if oficio_id is not None:
        oficio = db.session.get(Oficio, oficio_id)
        if not oficio:
            raise ValueError("El oficio indicado no existe.")
        if oficio.comprobacion_id is None or oficio.comprobacion_id != comprobacion_id:
            raise ValueError(
                "La comprobación del contexto no coincide con la comprobación del oficio indicado."
            )

    ex = db.session.query(Expediente).filter_by(numero_expediente=numero, anio=anio_str).first()
    if ex:
        if ex.deleted_at is not None:
            ex.deleted_at = None

        if oficio_id is None:
            if ex.oficio_id is not None:
                raise ValueError(
                    f"El Expediente {label} ya está asociado a un oficio."
                )
            if ex.notificacion_id is not None:
                raise ValueError(
                    f"El Expediente {label} ya existe vinculado a otra notificación o contexto."
                )
            if ex.comprobacion_id is not None and ex.comprobacion_id != comprobacion_id:
                raise ValueError(
                    f"El Expediente {label} ya existe y está asociado a otra comprobación."
                )
            if ex.comprobacion_id is None:
                ex.comprobacion_id = comprobacion_id
            db.session.add(ex)
            return ex

        if ex.oficio_id is None:
            raise ValueError(
                f"El Expediente {label} ya existe vinculado solo a comprobación; "
                "no corresponde al flujo de expediente de oficio."
            )
        if ex.oficio_id != oficio_id:
            raise ValueError(
                f"El Expediente {label} ya existe y está asociado a otro oficio."
            )
        if ex.comprobacion_id is not None and ex.comprobacion_id != comprobacion_id:
            raise ValueError(
                f"El Expediente {label} ya existe y está asociado a otra comprobación."
            )
        if ex.comprobacion_id is None:
            ex.comprobacion_id = comprobacion_id
        db.session.add(ex)
        return ex

    ex = Expediente(
        numero_expediente=numero,
        anio=anio_str,
        comprobacion_id=comprobacion_id,
        oficio_id=oficio_id,
    )
    db.session.add(ex)
    db.session.flush()
    return ex
