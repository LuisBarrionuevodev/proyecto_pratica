"""Contrato grilla: lista ``inspectores`` canónica vs slots inspector1/2/3."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn


def _base_tipo_inspeccion() -> dict:
    return {
        "tipo_actuacion": "INSPECCION",
        "orden_trabajo_numero": "123456",
        "fecha_actuacion": "31/12/2025",
        "calle": "San Martín",
        "numero": "100",
        "rubro_nombre": "Bar",
        "doc_nro": "30123456",
    }


def test_inspectores_lista_cuatro_nombres_mapea_completo(app) -> None:
    data = {
        **_base_tipo_inspeccion(),
        "inspectores": ["Uno", "Dos", "Tres", "Cuatro"],
    }
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(data)
        payload = map_actuacion_row(row)
    assert payload["inspectores"] == ["Uno", "Dos", "Tres", "Cuatro"]


def test_inspectores_tiene_prioridad_sobre_slots(app) -> None:
    data = {
        **_base_tipo_inspeccion(),
        "inspectores": ["A", "B"],
        "inspector1": "Z",
        "inspector2": "Z",
        "inspector3": "Z",
    }
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(data)
        payload = map_actuacion_row(row)
    assert payload["inspectores"] == ["A", "B"]


def test_sin_inspectores_key_usa_slots(app) -> None:
    data = {**_base_tipo_inspeccion(), "inspector1": "S1", "inspector3": "S3"}
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(data)
        payload = map_actuacion_row(row)
    assert payload["inspectores"] == ["S1", "S3"]


def test_tipo_sin_inspectores_falla(app) -> None:
    data = {**_base_tipo_inspeccion()}
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            ActuacionGridRowIn.model_validate(data)
    assert "inspectores" in str(exc.value)

