"""Tests de normalización de estado de iniciador (bandejas editables)."""

from __future__ import annotations

import enum

import pytest

from app.utils.iniciador_estado import es_estado_iniciador_pendiente, normalize_estado_iniciador


class _EstadoFake(enum.Enum):
    PENDIENTE = "PENDIENTE"
    CUMPLIDO = "CUMPLIDO"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("PENDIENTE", "PENDIENTE"),
        ("  PENDIENTE  ", "PENDIENTE"),
        (_EstadoFake.PENDIENTE, "PENDIENTE"),
        (None, None),
    ],
)
def test_normalize_estado_iniciador(raw: object, expected: str | None) -> None:
    assert normalize_estado_iniciador(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("PENDIENTE", True),
        (_EstadoFake.PENDIENTE, True),
        ("CUMPLIDO", False),
        (_EstadoFake.CUMPLIDO, False),
        (None, False),
    ],
)
def test_es_estado_iniciador_pendiente(raw: object, expected: bool) -> None:
    assert es_estado_iniciador_pendiente(raw) is expected
