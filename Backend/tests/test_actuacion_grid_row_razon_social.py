"""ActuacionGridRowIn: razón social en contribuyente; ec5_uuid ignorado en canal actas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn


def _fila_base():
    return {
        "orden_trabajo_numero": "123456",
        "fecha_actuacion": "31/12/2025",
        "tipo_actuacion": "INSPECCION",
        "calle": "San Martín",
        "numero": "100",
        "rubro_nombre": "Bar",
        "doc_nro": "30123456",
        "inspector1": "Inspector Uno",
    }


def test_razon_social_sin_doc_falla(app):
    data = _fila_base()
    data.pop("doc_nro", None)
    data["razon_social"] = "SA ACME"
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            ActuacionGridRowIn.model_validate(data)
    errs = exc.value.errors()
    assert any(e.get("loc") == ("doc_nro",) for e in errs)


def test_razon_social_con_doc_ok_y_mapper(app):
    data = _fila_base()
    data["razon_social"] = "  SA ACME  "
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(data)
        payload = map_actuacion_row(row)
    assert payload["contribuyente"]["razon_social"] == "SA ACME"


def test_ec5_uuid_extra_se_ignora(app):
    data = _fila_base()
    data["ec5_uuid"] = "550e8400-e29b-41d4-a716-446655440000"
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(data)
    assert not hasattr(row, "ec5_uuid")
