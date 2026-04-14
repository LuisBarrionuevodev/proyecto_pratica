"""
Días hábiles Argentina: excluye sábado, domingo y feriados nacionales.

Regla de notificación (dominio):
- El día de la notificación no cuenta.
- El plazo arranca el **próximo** día hábil posterior a ``fecha_notificacion``.
- ``plazo_dias + prorroga_dias`` es la cantidad de **días hábiles** del plazo (inclusive el día de inicio).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Callable, Optional

from app.shared.utils.feriados_nacionales_ar import es_feriado_nacional_ar

HolidayPredicate = Callable[[date], bool]


def es_fin_de_semana(d: date) -> bool:
    return d.weekday() >= 5


def es_dia_habil(
    d: date,
    *,
    es_feriado: Optional[HolidayPredicate] = None,
) -> bool:
    """
    True si ``d`` es día hábil (no sábado/domingo y no feriado nacional).

    ``es_feriado``: inyección opcional para tests (si es None, usa feriados AR por defecto).
    """
    if es_fin_de_semana(d):
        return False
    fn = es_feriado if es_feriado is not None else es_feriado_nacional_ar
    return not fn(d)


def siguiente_dia_habil_posterior(
    d: date,
    *,
    es_feriado: Optional[HolidayPredicate] = None,
) -> date:
    """
    Primer día hábil estrictamente **posterior** a ``d`` (el día ``d`` no cuenta).
    """
    cur = d + timedelta(days=1)
    while not es_dia_habil(cur, es_feriado=es_feriado):
        cur += timedelta(days=1)
    return cur


def _nth_dia_habil_desde_inicio_inclusive(
    inicio: date,
    n: int,
    *,
    es_feriado: Optional[HolidayPredicate] = None,
) -> date:
    """
    ``n``-ésimo día hábil contando ``inicio`` como día 1 (``inicio`` debe ser hábil).

    Raises:
        ValueError: si ``n`` < 1 o ``inicio`` no es hábil.
    """
    if n < 1:
        raise ValueError("n debe ser >= 1")
    if not es_dia_habil(inicio, es_feriado=es_feriado):
        raise ValueError("inicio debe ser un día hábil")
    current = inicio
    restantes = n - 1
    while restantes > 0:
        current += timedelta(days=1)
        if es_dia_habil(current, es_feriado=es_feriado):
            restantes -= 1
    return current


def calcular_fecha_vencimiento_notificacion_habiles(
    fecha_notificacion: date,
    total_dias_habiles: int,
    *,
    es_feriado: Optional[HolidayPredicate] = None,
) -> date:
    """
    Fecha de vencimiento operativa con plazo en días hábiles.

    - No cuenta el día de ``fecha_notificacion``.
    - El primer día del plazo es el próximo día hábil posterior.
    - ``total_dias_habiles`` = plazo + prórrogas (suma de días hábiles a aplicar).

    Si ``total_dias_habiles`` <= 0, devuelve ``fecha_notificacion`` (compatibilidad con edge improbable).
    """
    total = int(total_dias_habiles)
    if total <= 0:
        return fecha_notificacion
    inicio = siguiente_dia_habil_posterior(fecha_notificacion, es_feriado=es_feriado)
    return _nth_dia_habil_desde_inicio_inclusive(inicio, total, es_feriado=es_feriado)
