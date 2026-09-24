from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Actuaciones, Comprobacion
from app.utils.actas import acta_6
from app.domains.actuaciones.attach.acta_reactivation_helpers import (
    otra_actuacion_usa_comprobacion,
)


def attach_comprobacion(actuacion: Actuaciones, data: Optional[Dict[str, Any]]) -> None:
    """
    Adjunta el acta de Comprobación a una Actuación.

    Reglas:
    - Unicidad lógica del acta: `(numero_acta, anio)`.
    - No se reutiliza una fila `Comprobacion` ya existente para enganchar otra actuación:
      si el par ya existe en BD y esta actuación aún no tenía la suya, es conflicto.
    - Si `actuacion.comprobacion_id` ya apunta a una fila, solo se actualiza esa misma fila.

    Valida `motivo` como obligatorio (no vacío tras `strip()`).

    Args:
        actuacion: Actuación destino (debe tener `id`, `anio`, `mes` y opcionalmente `tipo`).
        data: dict opcional con `acta_num` y `motivo`.

    Returns:
        None

    Raises:
        ValueError: si `motivo` es vacío.
        ValueError: conflicto de acta ya existente / ya vinculada a otra actuación.
    """
    if not data:
        return

    acta_num = acta_6(data.get("acta_num"))
    if not acta_num:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    motivo = (data.get("motivo") or "").strip()
    if not motivo:
        raise ValueError("Motivo de comprobación es obligatorio.")

    comp: Optional[Comprobacion] = None

    if actuacion.comprobacion_id:
        comp = db.session.get(Comprobacion, actuacion.comprobacion_id)
        if comp:
            otra_misma_clave = db.session.query(Comprobacion).filter_by(numero_acta=acta_num, anio=anio).first()
            if otra_misma_clave and otra_misma_clave.id != comp.id:
                raise ValueError(
                    f"La Comprobación {acta_num}/{anio} ya existe y está asociada a otra actuación."
                )

            if comp.deleted_at is not None:
                comp.deleted_at = None
            comp.numero_acta = acta_num
            comp.anio = anio
            comp.mes = mes
            comp.motivo = motivo
            db.session.add(comp)

    if not comp:
        existente = db.session.query(Comprobacion).filter_by(numero_acta=acta_num, anio=anio).first()
        if existente:
            if otra_actuacion_usa_comprobacion(int(existente.id), int(actuacion.id)):
                raise ValueError(
                    f"La Comprobación {acta_num}/{anio} ya existe y está asociada a otra actuación."
                )
            if existente.deleted_at is not None:
                existente.deleted_at = None
            existente.numero_acta = acta_num
            existente.anio = anio
            existente.mes = mes
            existente.motivo = motivo
            comp = existente
            db.session.add(comp)
        else:
            comp = Comprobacion(numero_acta=acta_num, anio=anio, mes=mes, motivo=motivo)
            db.session.add(comp)

    db.session.flush()

    if actuacion.tipo is not None:
        existe_mismo_tipo = (
            Actuaciones.query.filter(
                Actuaciones.id != actuacion.id,
                Actuaciones.anio == anio,
                Actuaciones.tipo == actuacion.tipo,
                Actuaciones.comprobacion_id == comp.id,
            ).first()
        )
        if existe_mismo_tipo:
            raise ValueError(
                f"La Comprobación {acta_num}/{anio} ya existe y está asociada a otra actuación."
            )

    actuacion.comprobacion_id = comp.id
