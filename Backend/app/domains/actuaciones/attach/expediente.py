from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Expediente
from app.utils.actas import acta_6


def attach_expediente(
    data: Optional[Dict[str, Any]],
    comprobacion_id: Optional[int],
    oficio_id: Optional[int],
) -> Optional[Expediente]:
    """
    Resuelve (get o create) un `Expediente` a partir de un payload parcial.

    Identificación:
    - Se identifica por `(numero_expediente, anio)` donde `anio` en DB es string/varchar.

    Reglas / comportamiento:
    - Si `data` es `None` -> devuelve `None`.
    - `numero` y `anio` son obligatorios; si falta alguno -> `ValueError`.
    - Normaliza `numero` con `acta_6`.
    - Convierte `anio` a `str` antes de consultar/crear.
    - Si existe el expediente -> lo devuelve (no modifica nada).
    - Si no existe:
        - Crea un `Expediente` con `numero_expediente`, `anio` (string), `comprobacion_id`, `oficio_id`.
        - Hace `db.session.add(...)` y `db.session.flush()` (NO hace commit/rollback).
        - Devuelve la instancia creada.

    Args:
        data: diccionario con claves esperadas:
            - `numero`: número de expediente
            - `anio`: año de expediente (se guarda como string)
        comprobacion_id: id de comprobación a asociar (opcional).
        oficio_id: id de oficio a asociar (opcional).

    Returns:
        `Expediente` existente o creado, o `None` si no se envía `data`.

    Raises:
        ValueError: si se envía `data` pero falta `numero` o `anio`.
    """
    if not data:
        return None

    numero = acta_6(data.get("numero"))
    anio = data.get("anio")

    if not numero or anio is None:
        raise ValueError("Si cargás expediente, número y año son obligatorios.")

    anio_str = str(anio)

    ex = db.session.query(Expediente).filter_by(numero_expediente=numero, anio=anio_str).first()
    if ex:
        # restore si estaba soft-deleted y reasociar
        if ex.deleted_at is not None:
            ex.deleted_at = None
        ex.comprobacion_id = comprobacion_id
        ex.oficio_id = oficio_id
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
