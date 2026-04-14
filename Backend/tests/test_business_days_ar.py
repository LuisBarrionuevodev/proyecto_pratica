"""Días hábiles AR: vencimiento de notificación y feriados."""

from __future__ import annotations

from datetime import date

import pytest

from app.domains.actuaciones.services.notificacion_timing_service import calcular_fecha_vencimiento
from app.shared.utils.business_days_ar import (
    calcular_fecha_vencimiento_notificacion_habiles,
    es_dia_habil,
    siguiente_dia_habil_posterior,
)


def test_notificacion_lunes_plazo_cinco_habiles() -> None:
    # Lunes 9 mar 2026 → inicio mar 10; 5 hábiles termina lun 16 (salta finde 14-15).
    fn = date(2026, 3, 9)
    assert calcular_fecha_vencimiento(fn, 5, 0) == date(2026, 3, 16)


def test_notificacion_viernes_salta_fin_de_semana() -> None:
    # Vie 6 mar 2026 → próximo hábil lun 9; 5 hábiles hasta vie 13.
    assert calcular_fecha_vencimiento(date(2026, 3, 6), 5, 0) == date(2026, 3, 13)


def test_feriado_nacional_inyectado_en_medio() -> None:
    """Feriado extra solo en tests: empuja el cómputo."""
    fn = date(2026, 3, 9)  # lunes
    extra = date(2026, 3, 11)  # miércoles del mismo plazo

    def es_feriado(d: date) -> bool:
        return d == extra

    # Sin inyección sería 16 mar; con mié 11 inhábil debe correrse un día hábil.
    sin_extra = calcular_fecha_vencimiento_notificacion_habiles(fn, 5, es_feriado=None)
    con_extra = calcular_fecha_vencimiento_notificacion_habiles(fn, 5, es_feriado=es_feriado)
    assert sin_extra == date(2026, 3, 16)
    assert con_extra == date(2026, 3, 17)
    assert es_dia_habil(con_extra, es_feriado=es_feriado)


def test_prorroga_suma_dias_habiles() -> None:
    fn = date(2026, 3, 9)
    solo_plazo = calcular_fecha_vencimiento(fn, 5, 0)
    con_prorroga = calcular_fecha_vencimiento(fn, 5, 2)
    assert con_prorroga > solo_plazo
    # 2 días hábiles más desde el mismo inicio ⇒ 7 hábiles totales
    assert calcular_fecha_vencimiento_notificacion_habiles(fn, 7) == con_prorroga


def test_total_cero_devuelve_fecha_notificacion() -> None:
    fn = date(2026, 4, 1)
    assert calcular_fecha_vencimiento_notificacion_habiles(fn, 0) == fn


def test_siguiente_dia_habil_posterior_viernes() -> None:
    assert siguiente_dia_habil_posterior(date(2026, 3, 6)) == date(2026, 3, 9)
