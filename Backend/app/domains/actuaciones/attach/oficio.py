from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import date, datetime

from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models import Oficio


def _normalize_causa(value: Any) -> Optional[str]:
    """Causa persistida: None si vacía; strip para comparar con la BD."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _raise_if_numero_anio_unique_violation(exc: IntegrityError, label: str) -> None:
    """Traduce violación de unicidad ``(numero_oficio, anio)`` a mensaje de negocio."""
    orig_s = str(getattr(exc, "orig", exc)).lower()
    if "uq_of_numero" in orig_s or "numero_oficio" in orig_s:
        raise ValueError(f"El Oficio {label} ya existe.") from exc


def _raise_if_causa_inconsistent(
    causa_existente: Optional[str],
    causa_nueva: Optional[str],
    label: str,
) -> None:
    """Bloquea reutilizar un oficio existente con otra causa distinta."""
    if causa_existente is None or causa_nueva is None:
        return
    if causa_existente != causa_nueva:
        raise ValueError(
            f'El Oficio {label} ya existe con otra causa ("{causa_existente}").'
        )


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
    - Misma clave + causa distinta a la ya persistida: `ValueError` (inconsistencia de identidad).
    - La causa **no** es única por año: varios oficios distintos pueden compartir causa.

    Args:
        data: `numero`, `anio`, opcionalmente `fecha_oficio`, `juzgado_id`, `causa`.
        comprobacion_id: FK de comprobación del contexto (obligatoria si hay `data`).

    Returns:
        `Oficio` existente o creado, o `None` si no hay `data`.

    Raises:
        ValueError: validación, conflicto de contexto o inconsistencia de causa en oficio existente.
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
            causa_n = _normalize_causa(data.get("causa"))
            _raise_if_causa_inconsistent(of.causa, causa_n, label)
            of.causa = causa_n
        db.session.add(of)
        try:
            db.session.flush()
        except IntegrityError as exc:
            _raise_if_numero_anio_unique_violation(exc, label)
            raise
        return of

    causa_n = _normalize_causa(data.get("causa"))
    of = Oficio(
        numero_oficio=numero_s,
        anio=anio_i,
        fecha_oficio=fecha_oficio,
        causa=causa_n,
        juzgado_id=data.get("juzgado_id"),
        comprobacion_id=comprobacion_id,
    )
    db.session.add(of)
    try:
        db.session.flush()
    except IntegrityError as exc:
        _raise_if_numero_anio_unique_violation(exc, label)
        raise
    return of
