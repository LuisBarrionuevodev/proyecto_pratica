"""STAB-4: contraproducencia sin default NO_HUBO en edición / mapper."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.update_service import aplicar_payload_actuacion


def _fila_con_acta():
    return {
        "orden_trabajo_numero": "123456",
        "fecha_actuacion": "31/12/2025",
        "tipo_actuacion": "INSPECCION",
        "calle": "San Martín",
        "numero": "100",
        "rubro_nombre": "Bar",
        "doc_nro": "30123456",
        "inspector1": "Inspector Uno",
        "acta_inspeccion_num": "000042",
    }


def test_sin_contraproducencia_no_default_no_hubo(app) -> None:
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(_fila_con_acta())
    assert row.contraproducencia is None


def test_contraproducencia_explicita_no_hubo_ok(app) -> None:
    data = {**_fila_con_acta(), "contraproducencia": "NO_HUBO"}
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(data)
    assert row.contraproducencia is not None
    assert str(row.contraproducencia).replace(" ", "_").upper().find("NO") >= 0


def test_mapper_omite_contraproducencia_si_none(app) -> None:
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(_fila_con_acta())
        payload = map_actuacion_row(row)
    assert "contraproducencia" not in payload


def test_mapper_incluye_contraproducencia_explicita(app) -> None:
    data = {**_fila_con_acta(), "contraproducencia": "LOCAL CERRADO"}
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(data)
        payload = map_actuacion_row(row)
    assert payload.get("contraproducencia") == "LOCAL CERRADO"


def test_solo_ot_fecha_exige_contraproducencia_explicita(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            ActuacionGridRowIn.model_validate(
                {
                    "orden_trabajo_numero": "000001",
                    "fecha_actuacion": "01/03/2026",
                }
            )
    assert "contraproducencia" in str(exc.value).lower()


def test_aplicar_payload_sin_contraproducencia_no_pisa_existente(app) -> None:
    act = SimpleNamespace(contraproducencia="LOCAL CERRADO", tipo=None, nombre_local=None)
    with app.app_context():
        aplicar_payload_actuacion(
            act,  # type: ignore[arg-type]
            {"fecha_actuacion": "01/03/2026"},
            ejecutar_resolver_previas=False,
        )
    assert act.contraproducencia == "LOCAL CERRADO"
