from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Oficio


def attach_oficio(data: Optional[Dict[str, Any]], comprobacion_id: Optional[int]) -> Optional[Oficio]:
    """
    Resuelve (get o create) un `Oficio` a partir de un payload parcial.

    Identificación:
    - Se identifica por `(numero_oficio, anio)`.

    Reglas / comportamiento:
    - Si `data` es `None` -> devuelve `None`.
    - Si falta `numero` o `anio` -> `ValueError`.
    - Si existe el oficio -> lo devuelve (no modifica nada).
    - Si no existe:
        - Crea un `Oficio` con `numero_oficio`, `anio`, `causa` y `comprobacion_id`.
        - Hace `db.session.add(...)` y `db.session.flush()` (NO hace commit/rollback).
        - Devuelve la instancia creada.

    Args:
        data: diccionario con claves esperadas:
            - `numero`: número de oficio
            - `anio`: año de oficio
            - `causa`: causa (opcional)
        comprobacion_id: id de comprobación a asociar (opcional).

    Returns:
        `Oficio` existente o creado, o `None` si no se envía `data`.

    Raises:
        ValueError: si se envía `data` pero falta `numero` o `anio`.
    """
    if not data:
        return None

    numero = data.get("numero")
    anio = data.get("anio")

    if not numero or anio is None:
        raise ValueError("Si cargás oficio, número y año son obligatorios.")

    of = Oficio.query.filter_by(numero_oficio=str(numero).strip(), anio=int(anio)).first()
    if of:
        return of

    of = Oficio(
        numero_oficio=str(numero).strip(),
        anio=int(anio),
        causa=data.get("causa"),
        comprobacion_id=comprobacion_id,
    )
    db.session.add(of)
    db.session.flush()
    return of
