from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Actuaciones, Clausura
from app.utils.actas import acta_6
from app.services.actuaciones.attach.uniqueness import (
    asegurar_acta_libre_para_actuacion,
    asegurar_acta_no_usada_en_otra,
)


def attach_clausura(actuacion: Actuaciones, data: Optional[Dict[str, Any]], crear: bool = True) -> None:
    """
    Adjunta (upsert) el acta de Clausura a una Actuación.

    Comportamiento (sin cambiar queries):
    - Si `data` es `None` o no trae `acta_num` -> no hace nada.
    - Normaliza `acta_num` con `acta_6`; si queda vacío -> no hace nada.
    - Determina `anio` y `mes` desde la propia `actuacion`.
    - Valida unicidad del acta:
        - En creación (`crear=True`): el `(numero_acta, anio)` no puede estar asociado a otra actuación.
        - En update (`crear=False`): permite si está libre (`actuacion_id` None) o ya asociada a esta actuación.
    - Si ya existe una `Clausura` con `actuacion_id == actuacion.id`, actualiza sus campos.
    - Si no existe por `actuacion_id`, busca por `(numero_acta, anio)`:
        - Si existe, la re-asocia a la actuación.
        - Si no existe, crea una nueva.

    Args:
        actuacion: Actuación destino (debe tener `id`, `anio`, `mes`).
        data: dict opcional con `acta_num`.
        crear: si es `True`, aplica reglas de unicidad de creación; si es `False`, reglas de update.

    Returns:
        None

    Raises:
        ValueError: si el acta ya está asociada a otra actuación (según reglas de unicidad).
    """
    if not data or not data.get("acta_num"):
        return

    numero = acta_6(data["acta_num"])
    if not numero:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    if crear:
        asegurar_acta_no_usada_en_otra(Clausura, numero, anio, actuacion.id)
    else:
        asegurar_acta_libre_para_actuacion(Clausura, numero, anio, actuacion.id)

    actual = Clausura.query.filter_by(actuacion_id=actuacion.id).first()
    if actual:
        actual.numero_acta = numero
        actual.anio = anio
        actual.mes = mes
        db.session.add(actual)
        return

    cl = Clausura.query.filter_by(numero_acta=numero, anio=anio).first()
    if cl:
        cl.actuacion_id = actuacion.id
        db.session.add(cl)
        return

    cl = Clausura(numero_acta=numero, anio=anio, mes=mes, actuacion_id=actuacion.id)
    db.session.add(cl)
