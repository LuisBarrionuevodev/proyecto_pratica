"""
Feriados nacionales Argentina (inamovibles + móviles frecuentes).

Extensible: sumar fechas a ``EXTRA_DATES_BY_YEAR`` o ampliar ``_fixed_mm_dd``.
Fuente de verdad operativa hasta integrar API/carga administrativa.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from typing import FrozenSet


def _easter_sunday(year: int) -> date:
    """Algoritmo de Meeus/Jones/Butcher (Gregorian)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


# Inamovibles habituales + feriados móviles derivados de Pascua / Carnaval.
# Ajustar según calendario oficial ANSES / Ministerio Interior cuando se formalice carga.
_FIXED_MM_DD: tuple[tuple[int, int], ...] = (
    (1, 1),  # Año Nuevo
    (3, 24),  # Día de la Memoria por la Verdad y la Justicia
    (4, 2),  # Día del Veterano y de los Caídos en la Guerra de Malvinas
    (5, 1),  # Día del trabajador
    (5, 25),  # Revolución de Mayo
    (6, 17),  # Paso a la inmortalidad del General Martín Miguel de Güemes
    (6, 20),  # Paso a la inmortalidad del General Manuel Belgrano
    (7, 9),  # Día de la Independencia
    (12, 8),  # Inmaculada Concepción de María
    (12, 25),  # Navidad
)

# Puentes / fechas extra por año (placeholder extensible).
EXTRA_DATES_BY_YEAR: dict[int, frozenset[date]] = {}


@lru_cache(maxsize=64)
def feriados_nacionales_ar(year: int) -> FrozenSet[date]:
    """
    Conjunto de fechas no laborables por feriado nacional en el año dado.

    Incluye inamovibles (mismo calendario cada año), Carnaval (Lun y Mar),
    Viernes Santo y cualquier fecha extra en ``EXTRA_DATES_BY_YEAR``.
    """
    out: set[date] = {date(year, m, d) for m, d in _FIXED_MM_DD}
    easter = _easter_sunday(year)
    # Carnaval: lunes y martes previos al Miércoles de Ceniza (46 días antes de Pascua).
    ash_wednesday = easter - timedelta(days=46)
    carnival_tuesday = ash_wednesday - timedelta(days=1)
    carnival_monday = ash_wednesday - timedelta(days=2)
    out.add(carnival_monday)
    out.add(carnival_tuesday)
    # Viernes Santo
    out.add(easter - timedelta(days=2))
    out.update(EXTRA_DATES_BY_YEAR.get(year, frozenset()))
    return frozenset(out)


def es_feriado_nacional_ar(d: date) -> bool:
    """True si ``d`` es feriado nacional según ``feriados_nacionales_ar``."""
    return d in feriados_nacionales_ar(d.year)
