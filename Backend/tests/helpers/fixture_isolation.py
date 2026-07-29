"""Helpers aislados para fixtures en BD compartida (solo tests)."""

from __future__ import annotations

import random
from datetime import date, timedelta
from uuid import uuid4


def fecha_fixture_aislada(*, anio: int = 2090) -> date:
    """Día único por corrida (evita uq fecha+turno+numero y colisiones entre tests)."""
    n = int(uuid4().hex[:8], 16) % 3650
    return date(anio, 1, 1) + timedelta(days=n)


def fecha_ruta_aislada_mismo_anio(anio: int = 2026) -> date:
    """Día único dentro del año de la OT/ruta."""
    n = int(uuid4().hex[:8], 16) % 364
    return date(anio, 1, 1) + timedelta(days=n)


def uniq_ruta_numero() -> int:
    """Número de ruta único (SmallInteger; evita uq fecha+turno+numero)."""
    return int(uuid4().hex[:4], 16) % 31_999 + 2


def unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def fecha_vencimiento_vencida_aislada() -> date:
    """Vencimiento en el pasado (<= today) y distinto por corrida."""
    n = int(uuid4().hex[:6], 16) % 3650
    return date(2000, 1, 1) + timedelta(days=n)
