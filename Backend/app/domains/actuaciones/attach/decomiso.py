from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Actuaciones, Decomiso
from app.utils.actas import acta_6
from .uniqueness import (
    asegurar_acta_libre_para_actuacion,
    asegurar_acta_no_usada_en_otra,
)


def attach_decomiso(actuacion: Actuaciones, data: Optional[Dict[str, Any]], crear: bool = True) -> None:
    """
    Adjunta (upsert) el acta de Decomiso a una Actuación.

    Comportamiento (sin cambiar lógica ni queries):
    - Si `data` es `None` o no trae `acta_num` -> no hace nada.
    - Normaliza `acta_num` con `acta_6`; si queda vacío -> no hace nada.
    - Valida `kilos_total`:
        - obligatorio (no puede ser `None`)
        - convertible a `float`
        - debe ser `> 0`
    - Determina `anio` y `mes` desde la propia `actuacion`.
    - Valida unicidad del acta:
        - En creación (`crear=True`): el `(numero_acta, anio)` no puede estar asociado a otra actuación.
        - En update (`crear=False`): permite si está libre (`actuacion_id` None) o ya asociada a esta actuación.
    - Si ya existe un `Decomiso` con `actuacion_id == actuacion.id`, actualiza sus campos.
    - Si no existe por `actuacion_id`, busca por `(numero_acta, anio)`:
        - Si existe, la re-asocia a la actuación y actualiza `mes`/`cantidad`.
        - Si no existe, crea uno nuevo.

    Args:
        actuacion: Actuación destino (debe tener `id`, `anio`, `mes`).
        data: dict opcional con `acta_num` y `kilos_total`.
        crear: si es `True`, aplica reglas de unicidad de creación; si es `False`, reglas de update.

    Returns:
        None

    Raises:
        ValueError: si `kilos_total` falta, es inválido o no es `> 0`.
        ValueError: si el acta ya está asociada a otra actuación (según reglas de unicidad).
    """
    if not data or not data.get("acta_num"):
        return

    numero = acta_6(data["acta_num"])
    if not numero:
        return

    kilos = data.get("kilos_total")
    if kilos is None:
        raise ValueError("Kilos de decomiso es obligatorio.")
    try:
        kilos = float(kilos)
    except Exception:
        raise ValueError("Kilos de decomiso inválido.")
    if kilos <= 0:
        raise ValueError("Kilos de decomiso debe ser > 0.")

    anio = actuacion.anio
    mes = actuacion.mes

    if crear:
        asegurar_acta_no_usada_en_otra(Decomiso, numero, anio, actuacion.id)
    else:
        asegurar_acta_libre_para_actuacion(Decomiso, numero, anio, actuacion.id)

    actual = Decomiso.query.filter_by(actuacion_id=actuacion.id).first()
    if actual:
        actual.numero_acta = numero
        actual.anio = anio
        actual.mes = mes
        actual.cantidad = kilos
        db.session.add(actual)
        return

    dec = Decomiso.query.filter_by(numero_acta=numero, anio=anio).first()
    if dec:
        dec.actuacion_id = actuacion.id
        dec.mes = mes
        dec.cantidad = kilos
        db.session.add(dec)
        return

    dec = Decomiso(numero_acta=numero, anio=anio, mes=mes, cantidad=kilos, actuacion_id=actuacion.id)
    db.session.add(dec)
