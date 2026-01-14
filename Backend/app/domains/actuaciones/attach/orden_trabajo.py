from __future__ import annotations

from typing import Any

from app.database import db
from app.models import OrdenTrabajo
from app.utils.actas import acta_6
from app.utils.fechas import parse_fecha_grid


def get_or_create_orden_trabajo(numero_ot: Any, fecha_str: Any) -> OrdenTrabajo:
    """
    Resuelve (get o create) una `OrdenTrabajo` identificándola por `(numero_acta, anio)`.

    Reglas / comportamiento:
    - El `anio` y `mes` se calculan desde `fecha_str` con `parse_fecha_grid`.
    - El número de OT/acta se normaliza con `acta_6` (6 dígitos si es numérico).
    - Si el número no existe/queda vacío -> `ValueError`.
    - Si ya existe una OT con ese `(numero_acta, anio)` -> la devuelve.
    - Si no existe:
        - Crea una OT con `numero_acta`, `anio`, `mes`.
        - Hace `db.session.add(...)` y `db.session.flush()` (NO hace commit).
        - Devuelve la instancia creada.

    Args:
        numero_ot: número de orden de trabajo / acta (cualquier tipo, se normaliza a string).
        fecha_str: fecha en formatos aceptados por `parse_fecha_grid`.

    Returns:
        `OrdenTrabajo` existente o creada.

    Raises:
        ValueError: si el número de OT es obligatorio y no se puede obtener un valor válido.
        ValueError: si `fecha_str` no cumple el formato esperado por `parse_fecha_grid`.
    """
    mes, anio, _ = parse_fecha_grid(fecha_str)
    numero = acta_6(numero_ot)
    if not numero:
        raise ValueError("Orden de trabajo es obligatoria.")

    ot = OrdenTrabajo.query.filter_by(numero_acta=numero, anio=anio).first()
    if ot:
        return ot

    ot = OrdenTrabajo(numero_acta=numero, anio=anio, mes=mes)
    db.session.add(ot)
    db.session.flush()
    return ot
