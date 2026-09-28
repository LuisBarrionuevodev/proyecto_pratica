"""RELEVAMIENTO-HOTFIX.2 — fecha opcional en schema de grilla (sin relevador / sin DB)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domains.relevamientos.schemas.grid.relevamiento_row_in import RelevamientoGridRowIn

_CTX = {"allow_missing_relevador": True}


def _base_row(**overrides):
    return {
        "calle": "Calle Test",
        "numero": "10",
        **overrides,
    }


def test_schema_sin_key_fecha_ok():
    row = RelevamientoGridRowIn.model_validate(_base_row(), context=_CTX)
    assert row.fecha is None


def test_schema_fecha_null_ok():
    row = RelevamientoGridRowIn.model_validate(_base_row(fecha=None), context=_CTX)
    assert row.fecha is None


def test_schema_fecha_vacia_ok():
    row = RelevamientoGridRowIn.model_validate(_base_row(fecha=""), context=_CTX)
    assert row.fecha is None


def test_schema_fecha_explicita_valida():
    row = RelevamientoGridRowIn.model_validate(
        _base_row(fecha="2026-04-15"),
        context=_CTX,
    )
    assert row.fecha is not None
    assert row.fecha.isoformat() == "2026-04-15"


def test_schema_fecha_invalida_rechaza():
    with pytest.raises(ValidationError):
        RelevamientoGridRowIn.model_validate(
            _base_row(fecha="31/13/2026"),
            context=_CTX,
        )
