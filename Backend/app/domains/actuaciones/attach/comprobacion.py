from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Actuaciones, Comprobacion
from app.utils.actas import acta_6


def attach_comprobacion(actuacion: Actuaciones, data: Optional[Dict[str, Any]]) -> None:
    """
    Adjunta (upsert) el acta de Comprobación a una Actuación.

    Objetivo:
    - Evitar crear "basura" de comprobaciones duplicadas y mantener la misma regla de negocio
      (no repetir la misma comprobación en otra actuación del mismo `(anio, tipo)`).

    Comportamiento:
    - Si `data` es `None` -> no hace nada.
    - Normaliza `data["acta_num"]` con `acta_6`; si queda vacío -> no hace nada.
    - Valida `motivo` como obligatorio (no vacío tras `strip()`).

    Upsert:
    - Si `actuacion.comprobacion_id` existe:
        - Carga esa `Comprobacion` y actualiza `numero_acta`, `anio`, `mes`, `motivo`.
        - Antes de actualizar, verifica que NO exista otra `Comprobacion` con el mismo `(numero_acta, anio)`
          con `id` distinto. Si existe -> `ValueError("Acta de comprobación ya asociada a otra actuación")`.
    - Si NO existe `actuacion.comprobacion_id` (o no se pudo cargar):
        - Busca `Comprobacion` por `(numero_acta, anio)`.
        - Si no existe, la crea.
        - Si existe, actualiza `mes` y `motivo`.

    Regla de negocio:
    - La misma comprobación (mismo `comprobacion_id`) NO puede estar asociada a otra actuación del mismo `(anio, tipo)`.

    Al final:
    - Setea `actuacion.comprobacion_id = comp.id`.

    Args:
        actuacion: Actuación destino (debe tener `id`, `anio`, `mes` y opcionalmente `tipo`).
        data: dict opcional con `acta_num` y `motivo`.

    Returns:
        None

    Raises:
        ValueError: si `motivo` es vacío.
        ValueError: si el acta de comprobación ya está asociada a otra actuación.
        ValueError: si la comprobación ya está asociada a otra actuación del mismo tipo (mismo `(anio, tipo)`).
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

    # Caso 1: la actuación ya tiene una comprobación asociada -> actualizar esa
    if actuacion.comprobacion_id:
        comp = db.session.get(Comprobacion, actuacion.comprobacion_id)
        if comp:
            existente = db.session.query(Comprobacion).filter_by(numero_acta=acta_num, anio=anio).first()
            if existente and existente.id != comp.id:
                raise ValueError("Acta de comprobación ya asociada a otra actuación")

            if comp.deleted_at is not None:
                comp.deleted_at = None
            comp.numero_acta = acta_num
            comp.anio = anio
            comp.mes = mes
            comp.motivo = motivo
            db.session.add(comp)

    # Caso 2: no hay comprobación asociada (o no se pudo cargar) -> buscar/crear por acta+anio
    if not comp:
        comp = db.session.query(Comprobacion).filter_by(numero_acta=acta_num, anio=anio).first()
        if not comp:
            comp = Comprobacion(numero_acta=acta_num, anio=anio, mes=mes, motivo=motivo)
            db.session.add(comp)
            db.session.flush()
        else:
            # restore si estaba soft-deleted
            if comp.deleted_at is not None:
                comp.deleted_at = None
            comp.mes = mes
            comp.motivo = motivo
            db.session.add(comp)

    db.session.flush()

    # Regla negocio: misma comprobación NO puede repetirse en (anio,tipo)
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
                f"La Comprobación {acta_num}/{anio} ya está asociada a otra actuación del mismo tipo ({actuacion.tipo})."
            )

    actuacion.comprobacion_id = comp.id
