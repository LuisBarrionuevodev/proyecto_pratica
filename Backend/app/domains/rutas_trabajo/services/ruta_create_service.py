from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models import RutaTrabajo

from .auth_service import get_current_user_id_or_fallback


def create_ruta_trabajo(*, fecha: date, turno: str, observaciones: str | None) -> RutaTrabajo:
    """
    Crea una RutaTrabajo en estado BORRADOR.

    Reglas:
    - numero autogenerado por combinación (fecha, turno) como max(numero)+1.
    - utiliza enum de turno actual del modelo (MANIANA|TARDE).

    Errores:
    - ValueError: validaciones de negocio.
    """
    turno_value = (turno or "").strip().upper()
    if turno_value not in {"MANIANA", "TARDE"}:
        raise ValueError("turno inválido")

    max_numero = (
        db.session.query(func.max(RutaTrabajo.numero))
        .filter(
            RutaTrabajo.fecha == fecha,
            RutaTrabajo.turno == turno_value,
        )
        .scalar()
    )
    next_numero = int(max_numero or 0) + 1

    ruta = RutaTrabajo(
        fecha=fecha,
        turno=turno_value,
        estado_ruta="BORRADOR",
        numero=next_numero,
        observaciones=observaciones,
        created_by_user_id=get_current_user_id_or_fallback(),
    )
    db.session.add(ruta)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise RuntimeError("No se pudo crear la ruta por conflicto de numeración") from exc
    return ruta
