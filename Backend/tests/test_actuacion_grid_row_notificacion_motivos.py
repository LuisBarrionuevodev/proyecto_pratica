"""Regla ActuacionGridRowIn: acta de notificación ⇒ al menos un motivo."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn


def _fila_minima_con_acta_notificacion() -> dict:
    return {
        "tipo_actuacion": "INSPECCION",
        "orden_trabajo_numero": "123456",
        "fecha_actuacion": "31/12/2025",
        "calle": "San Martín",
        "numero": "100",
        "rubro_nombre": "Bar",
        "doc_nro": "30123456",
        "inspector1": "Inspector Uno",
        "acta_notificacion_num": "000042",
    }


def test_actuacion_grid_row_acta_notificacion_sin_motivo_falla(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            ActuacionGridRowIn.model_validate(_fila_minima_con_acta_notificacion())
    assert "notificacion_motivo_1" in str(exc.value)


def test_actuacion_grid_row_acta_notificacion_con_motivo_ok(app) -> None:
    data = _fila_minima_con_acta_notificacion()
    data["notificacion_motivo_1"] = "Higiene"
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(data)
    assert row.acta_notificacion_num
    assert row.notificacion_motivo_1 == "Higiene"
