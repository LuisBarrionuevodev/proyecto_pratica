from __future__ import annotations

from typing import Any, Optional

from app.database import db
from app.models import Actuaciones, Inspeccion
from app.utils.actas import acta_6
from app.services.actuaciones.attach.uniqueness import (
    asegurar_acta_libre_para_actuacion,
    asegurar_acta_no_usada_en_otra,
)


def attach_inspeccion(actuacion: Actuaciones, acta_num: Optional[Any], crear: bool = True) -> None:
    """
    Adjunta (upsert) el acta de Inspección a una Actuación.

    Comportamiento (sin cambiar queries):
    - Si `acta_num` es falsy o al normalizar con `acta_6` queda vacío -> no hace nada.
    - Determina `anio` y `mes` desde la propia `actuacion`.
    - Valida unicidad del acta:
        - En creación (`crear=True`): el `(numero_acta, anio)` no puede estar asociado a otra actuación.
        - En update (`crear=False`): permite si está libre (`actuacion_id` None) o ya asociada a esta actuación.
    - Si ya existe una `Inspeccion` con `actuacion_id == actuacion.id`, actualiza sus campos.
    - Si no existe por `actuacion_id`, busca por `(numero_acta, anio)`:
        - Si existe, la re-asocia a la actuación.
        - Si no existe, crea una nueva.

    Args:
        actuacion: Actuación destino (debe tener `id`, `anio`, `mes`).
        acta_num: número de acta (cualquier tipo, se normaliza con `acta_6`).
        crear: si es `True`, aplica reglas de unicidad de creación; si es `False`, reglas de update.

    Returns:
        None

    Raises:
        ValueError: si el acta ya está asociada a otra actuación (según las reglas de unicidad).
    """
    if not acta_num:
        return

    numero = acta_6(acta_num)
    if not numero:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    if crear:
        asegurar_acta_no_usada_en_otra(Inspeccion, numero, anio, actuacion.id)
    else:
        asegurar_acta_libre_para_actuacion(Inspeccion, numero, anio, actuacion.id)

    actual = Inspeccion.query.filter_by(actuacion_id=actuacion.id).first()
    if actual:
        actual.numero_acta = numero
        actual.anio = anio
        actual.mes = mes
        db.session.add(actual)
        return

    ins = Inspeccion.query.filter_by(numero_acta=numero, anio=anio).first()
    if ins:
        # si existe pero era de otra actuación, asegurar_* ya lo frenó
        ins.actuacion_id = actuacion.id
        db.session.add(ins)
        return

    ins = Inspeccion(numero_acta=numero, anio=anio, mes=mes, actuacion_id=actuacion.id)
    db.session.add(ins)
