"""Presenter de día del resumen operativo Completar trabajo."""

from __future__ import annotations

from datetime import date

from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    dia_resumen_completar_trabajo_pendientes,
)


def test_dia_resumen_con_pendientes_y_atrasado() -> None:
    hoy = date(2026, 6, 15)
    row = dia_resumen_completar_trabajo_pendientes(
        fecha_dia=date(2026, 6, 1),
        total=5,
        items_con_actuacion=8,
        hoy=hoy,
    )
    assert row["fecha"] == "2026-06-01"
    assert row["total"] == 5
    assert row["items_con_actuacion"] == 8
    assert row["hubo_actividad"] is True
    assert row["sin_pendientes_cierre"] is False
    assert row["categoria_calendario"] == "CON_PENDIENTES"
    assert row["atrasado"] is True


def test_dia_resumen_completo_sin_pendientes() -> None:
    hoy = date(2026, 6, 15)
    row = dia_resumen_completar_trabajo_pendientes(
        fecha_dia=date(2026, 6, 10),
        total=0,
        items_con_actuacion=4,
        hoy=hoy,
    )
    assert row["total"] == 0
    assert row["sin_pendientes_cierre"] is True
    assert row["categoria_calendario"] == "COMPLETO"
    assert row["atrasado"] is False


def test_dia_resumen_futuro_con_pendientes_no_atrasado() -> None:
    hoy = date(2026, 6, 15)
    futuro = dia_resumen_completar_trabajo_pendientes(
        fecha_dia=date(2026, 6, 20),
        total=1,
        items_con_actuacion=3,
        hoy=hoy,
    )
    assert futuro["atrasado"] is False
    assert futuro["categoria_calendario"] == "CON_PENDIENTES"
