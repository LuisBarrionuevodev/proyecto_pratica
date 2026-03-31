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


def _conflicto_causa_anio(
    causa: Optional[str],
    anio: int,
    *,
    exclude_oficio_id: Optional[int] = None,
) -> bool:
    """True si ya existe otro oficio con la misma causa y año (causa no nula)."""
    if causa is None:
        return False
    q = db.session.query(Oficio).filter(Oficio.anio == anio, Oficio.causa == causa)
    if exclude_oficio_id is not None:
        q = q.filter(Oficio.id != exclude_oficio_id)
    return q.first() is not None


def _raise_if_causa_anio_unique_violation(exc: IntegrityError, causa: Optional[str], anio: int) -> None:
    """Traduce violación de uq_of_causa_anio a mensaje de negocio."""
    orig_s = str(getattr(exc, "orig", exc))
    if "uq_of_causa_anio" not in orig_s:
        return
    c = causa if causa is not None else "?"
    raise ValueError(
        f'La causa "{c}" ya existe para el año {anio}.'
    ) from exc


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
    - Unicidad de negocio `(causa, anio)`: la misma causa no puede repetirse en el mismo año entre
      oficios distintos; sí puede repetirse en otros años.

    Args:
        data: `numero`, `anio`, opcionalmente `fecha_oficio`, `juzgado_id`, `causa`.
        comprobacion_id: FK de comprobación del contexto (obligatoria si hay `data`).

    Returns:
        `Oficio` existente o creado, o `None` si no hay `data`.

    Raises:
        ValueError: validación, conflicto de contexto o causa duplicada para el año.
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
            if _conflicto_causa_anio(causa_n, of.anio, exclude_oficio_id=of.id):
                raise ValueError(
                    f'La causa "{causa_n}" ya existe para el año {of.anio}.'
                )
            of.causa = causa_n
        db.session.add(of)
        try:
            db.session.flush()
        except IntegrityError as exc:
            cn = _normalize_causa(of.causa)
            _raise_if_causa_anio_unique_violation(exc, cn, of.anio)
            raise
        return of

    causa_n = _normalize_causa(data.get("causa"))
    if _conflicto_causa_anio(causa_n, anio_i):
        raise ValueError(f'La causa "{causa_n}" ya existe para el año {anio_i}.')

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
        _raise_if_causa_anio_unique_violation(exc, causa_n, anio_i)
        raise
    return of
