"""Validación de query params del resumen Completar trabajo por día."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.domains.actuaciones.schemas.completar_trabajo_pendientes_resumen_filters import (
    COMPLETAR_TRABAJO_PENDIENTES_RESUMEN_MAX_DIAS,
    CompletarTrabajoPendientesResumenQuery,
)


def test_resumen_parse_fechas_iso() -> None:
    q = CompletarTrabajoPendientesResumenQuery.model_validate(
        {"fecha_desde": "2026-02-01", "fecha_hasta": "2026-02-28"}
    )
    assert q.fecha_desde == date(2026, 2, 1)
    assert q.fecha_hasta == date(2026, 2, 28)


def test_resumen_rechaza_fecha_desde_mayor_que_hasta() -> None:
    with pytest.raises(ValidationError):
        CompletarTrabajoPendientesResumenQuery.model_validate(
            {"fecha_desde": "2026-03-10", "fecha_hasta": "2026-03-01"}
        )


def test_resumen_rechaza_rango_demasiado_largo() -> None:
    d0 = date(2026, 1, 1)
    d1 = d0 + timedelta(days=COMPLETAR_TRABAJO_PENDIENTES_RESUMEN_MAX_DIAS + 1)
    with pytest.raises(ValidationError):
        CompletarTrabajoPendientesResumenQuery.model_validate({"fecha_desde": d0.isoformat(), "fecha_hasta": d1.isoformat()})


def test_resumen_un_solo_dia_ok() -> None:
    d = date(2026, 5, 15)
    q = CompletarTrabajoPendientesResumenQuery.model_validate({"fecha_desde": d.isoformat(), "fecha_hasta": d.isoformat()})
    assert q.fecha_desde == q.fecha_hasta == d
