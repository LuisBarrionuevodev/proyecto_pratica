from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import date, datetime

from app.database import db
from app.models import Oficio


def _parse_fecha_oficio(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("fecha_oficio debe tener formato YYYY-MM-DD.") from exc


def _oficio_label(numero: str, anio: int) -> str:
    return f"{numero}/{anio}"


def attach_oficio(data: Optional[Dict[str, Any]], comprobacion_id: Optional[int]) -> Optional[Oficio]:
    """
    Resuelve (get o create) un `Oficio` ligado a una **comprobación concreta**.

    **Canal:** no se usa desde CargarActuacion ni CompletarTrabajo; el ingreso canónico de oficio
    es el flujo **Esperando oficio** (`complete_oficio_from_actuacion` → este attach).

    Identificación:
    - Clave natural `(numero_oficio, anio)`.

    Reglas:
    - Sin `data` -> `None` (no valida `comprobacion_id`).
    - Con `data`, `comprobacion_id` obligatoria (oficio siempre anclado a una comprobación).
    - Misma clave + misma comprobación: actualización no destructiva (`fecha_oficio`, `juzgado_id`,
      `causa`) y restauración de soft-delete; **nunca** cambiar `comprobacion_id` a otra distinta.
    - Misma clave + otra comprobación: `ValueError` (no reutilizar oficio entre comprobaciones).

    Args:
        data: `numero`, `anio`, opcionalmente `fecha_oficio`, `juzgado_id`, `causa`.
        comprobacion_id: FK de comprobación del contexto (obligatoria si hay `data`).

    Returns:
        `Oficio` existente o creado, o `None` si no hay `data`.

    Raises:
        ValueError: validación o conflicto de contexto.
    """
    if not data:
        return None

    if comprobacion_id is None:
        raise ValueError("Para cargar un oficio se requiere una comprobación asociada.")

    numero = data.get("numero")
    anio = data.get("anio")

    if not numero or anio is None:
        raise ValueError("Si cargás oficio, número y año son obligatorios.")
    numero_s = str(numero).strip()
    anio_i = int(anio)
    fecha_oficio = _parse_fecha_oficio(data.get("fecha_oficio"))
    label = _oficio_label(numero_s, anio_i)

    of = db.session.query(Oficio).filter_by(numero_oficio=numero_s, anio=anio_i).first()
    if of:
        if of.deleted_at is not None:
            of.deleted_at = None
        if of.comprobacion_id is not None and of.comprobacion_id != comprobacion_id:
            raise ValueError(
                f"El Oficio {label} ya existe y está asociado a otra comprobación."
            )
        if of.comprobacion_id is None:
            of.comprobacion_id = comprobacion_id
        if "fecha_oficio" in data:
            of.fecha_oficio = fecha_oficio
        if "juzgado_id" in data:
            of.juzgado_id = data.get("juzgado_id")
        if "causa" in data:
            of.causa = data.get("causa")
        db.session.add(of)
        return of

    of = Oficio(
        numero_oficio=numero_s,
        anio=anio_i,
        fecha_oficio=fecha_oficio,
        causa=data.get("causa"),
        juzgado_id=data.get("juzgado_id"),
        comprobacion_id=comprobacion_id,
    )
    db.session.add(of)
    db.session.flush()
    return of
