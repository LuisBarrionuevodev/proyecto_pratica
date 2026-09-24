"""Etapa 2: contratos cerrados — CargarActuacion (grid) y CompletarTrabajo sin oficio/expediente."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)


def test_cargar_actuacion_payload_valido_con_acta_ok(app) -> None:
    with app.app_context():
        row = ActuacionGridRowIn.model_validate(
            {
                "orden_trabajo_numero": "000001",
                "fecha_actuacion": "2026-03-01",
                "calle": "San Martin",
                "numero": "100",
                "acta_inspeccion_num": "000042",
            }
        )
    assert row.acta_inspeccion_num == "000042"


def test_cargar_actuacion_rechaza_oficio(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            ActuacionGridRowIn.model_validate(
                {
                    "orden_trabajo_numero": "000001",
                    "fecha_actuacion": "2026-03-01",
                    "calle": "San Martin",
                    "numero": "100",
                    "oficio_numero": "45",
                }
            )
    assert "oficio" in str(exc.value).lower() or "carga de actas" in str(exc.value).lower()


def test_cargar_actuacion_rechaza_expediente(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            ActuacionGridRowIn.model_validate(
                {
                    "orden_trabajo_numero": "000001",
                    "fecha_actuacion": "2026-03-01",
                    "calle": "San Martin",
                    "numero": "100",
                    "expediente_numero": "1234",
                }
            )
    assert "expediente" in str(exc.value).lower() or "carga de actas" in str(exc.value).lower()


def test_completar_trabajo_payload_valido_ok(app) -> None:
    with app.app_context():
        m = CompletarTrabajoCierreCompletoIn(
            tipo_actuacion="INSPECCION",
            acta_inspeccion_num="123456",
        )
    assert m.acta_inspeccion_num == "123456"


def test_completar_trabajo_rechaza_oficio(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            CompletarTrabajoCierreCompletoIn(
                tipo_actuacion="INSPECCION",
                acta_inspeccion_num="123456",
                oficio_numero="45",
            )
    assert "completar trabajo" in str(exc.value).lower() or "oficio" in str(exc.value).lower()


def test_completar_trabajo_rechaza_expediente(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            CompletarTrabajoCierreCompletoIn(
                tipo_actuacion="INSPECCION",
                acta_inspeccion_num="123456",
                expediente_numero="1234",
            )
    assert "completar trabajo" in str(exc.value).lower() or "expediente" in str(exc.value).lower()


def test_completar_trabajo_extra_forbid(app) -> None:
    with app.app_context():
        with pytest.raises(ValidationError):
            CompletarTrabajoCierreCompletoIn.model_validate(
                {
                    "tipo_actuacion": "INSPECCION",
                    "acta_inspeccion_num": "123456",
                    "oficio_fantasma": "x",
                }
            )
