from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.domains.actuaciones.services.expediente_reactivacion_service import (
    buscar_expediente_envio_comprobacion_reactivable,
    buscar_expediente_respuesta_oficio_reactivable,
)
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

    Reactivación: si existe fila soft-deleted en el **mismo** circuito (misma comprobación / mismo oficio),
    se reactiva esa fila en lugar de crear otra; no se reutiliza un expediente borrado de otro circuito
    aunque comparta número/año.

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

    ex_active = (
        db.session.query(Expediente)
        .filter_by(numero_expediente=numero, anio=anio_str)
        .filter(Expediente.deleted_at.is_(None))
        .first()
    )
    if ex_active:
        ex = ex_active
        if oficio_id is None:
            if ex.oficio_id is not None:
                raise ValueError(
                    f"El Expediente {label} ya está asociado a un oficio.",
                )
            if ex.notificacion_id is not None:
                raise ValueError(
                    f"El Expediente {label} ya existe vinculado a otra notificación o contexto.",
                )
            if ex.comprobacion_id is not None and ex.comprobacion_id != comprobacion_id:
                raise ValueError(
                    f"El Expediente {label} ya existe y está asociado a otra comprobación.",
                )
            if ex.comprobacion_id is None:
                ex.comprobacion_id = comprobacion_id
            db.session.add(ex)
            return ex

        if ex.oficio_id is None:
            raise ValueError(
                f"El Expediente {label} ya existe vinculado solo a comprobación; "
                "no corresponde al flujo de expediente de oficio.",
            )
        if ex.oficio_id != oficio_id:
            raise ValueError(
                f"El Expediente {label} ya existe y está asociado a otro oficio.",
            )
        if ex.comprobacion_id is not None and ex.comprobacion_id != comprobacion_id:
            raise ValueError(
                f"El Expediente {label} ya existe y está asociado a otra comprobación.",
            )
        if ex.comprobacion_id is None:
            ex.comprobacion_id = comprobacion_id
        db.session.add(ex)
        return ex

    if oficio_id is None:
        ex_del = buscar_expediente_envio_comprobacion_reactivable(
            comprobacion_id=int(comprobacion_id),
            numero_expediente=numero,
            anio=anio_str,
        )
        if ex_del:
            ex_del.deleted_at = None
            if ex_del.comprobacion_id is None:
                ex_del.comprobacion_id = comprobacion_id
            elif ex_del.comprobacion_id != comprobacion_id:
                raise ValueError(
                    f"El Expediente {label} estaba borrado en otro circuito de comprobación.",
                )
            db.session.add(ex_del)
            return ex_del
    else:
        ex_del = buscar_expediente_respuesta_oficio_reactivable(
            comprobacion_id=int(comprobacion_id),
            oficio_id=int(oficio_id),
            numero_expediente=numero,
            anio=anio_str,
        )
        if ex_del:
            ex_del.deleted_at = None
            if ex_del.comprobacion_id is None:
                ex_del.comprobacion_id = comprobacion_id
            elif ex_del.comprobacion_id != comprobacion_id:
                raise ValueError(
                    f"El Expediente {label} estaba borrado en otra comprobación.",
                )
            if ex_del.oficio_id is None:
                ex_del.oficio_id = oficio_id
            elif ex_del.oficio_id != oficio_id:
                raise ValueError(
                    f"El Expediente {label} estaba borrado asociado a otro oficio.",
                )
            db.session.add(ex_del)
            return ex_del

    ex = Expediente(
        numero_expediente=numero,
        anio=anio_str,
        comprobacion_id=comprobacion_id,
        oficio_id=oficio_id,
    )
    db.session.add(ex)
    db.session.flush()
    return ex
