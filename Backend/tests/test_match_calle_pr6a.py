"""Tests PR6A — fechas, tokens cortos y estrategias de match."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import pytest

from app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service import (
    match_calle,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import (
    expand_number_words,
    matching_token_set,
    significant_tokens,
)


@dataclass
class _FakeCalle:
    id: int
    nombre_canonico: str
    nombre_key: str
    canon_base: str


def _catalog_pr6a() -> list[_FakeCalle]:
    from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key

    rows = [
        ("Avenida General Roca", "pres gral j a roca"),
        ("Pasaje Coronel Jose Segundo Roca", "coronel jose segundo roca"),
        ("9 de Julio", "9 de julio"),
        ("24 De Septiembre", "24 de septiembre"),
        ("Santiago del Estero", "santiago del estero"),
        ("Pasaje Santiago de Liniers", "santiago de liniers"),
        ("Julio Prebisch", "julio prebisch"),
    ]
    out: list[_FakeCalle] = []
    for idx, (canon, base) in enumerate(rows, start=1):
        out.append(
            _FakeCalle(
                id=idx,
                nombre_canonico=canon,
                nombre_key=slug_key(canon),
                canon_base=base,
            )
        )
    return out


@pytest.fixture
def catalog_pr6a(monkeypatch: pytest.MonkeyPatch) -> list[_FakeCalle]:
    rows = _catalog_pr6a()

    def _get_by_key(nombre_key: str) -> Optional[_FakeCalle]:
        for r in rows:
            if r.nombre_key == nombre_key:
                return r
        return None

    def _get_by_canon_base(canon_base: str) -> List[_FakeCalle]:
        return [r for r in rows if r.canon_base == canon_base]

    def _get_by_nombre_canonico(nombre: str) -> Optional[_FakeCalle]:
        target = (nombre or "").strip().upper()
        for r in rows:
            if r.nombre_canonico.upper() == target:
                return r
        return None

    def _list_active_keys() -> List[Tuple[int, str, str, str]]:
        return [(r.id, r.canon_base, r.nombre_key, r.nombre_canonico) for r in rows]

    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service.get_by_key",
        _get_by_key,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service.get_by_canon_base",
        _get_by_canon_base,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service.get_by_nombre_canonico",
        _get_by_nombre_canonico,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service.list_active_keys",
        _list_active_keys,
    )
    return rows


def test_expand_number_words_no_corrupts_luna() -> None:
    assert expand_number_words("mate de luna") == "mate de luna"
    assert expand_number_words("fernando mate de luna") == "fernando mate de luna"


def test_expand_number_words_fechas() -> None:
    assert expand_number_words("nueve de julio") == "9 de julio"
    assert expand_number_words("9 julio") == "9 julio"
    assert expand_number_words("veinticuatro de septiembre") == "24 de septiembre"
    assert "24" in expand_number_words("veinticuatro septiembre")


def test_significant_tokens_conserva_numeros() -> None:
    assert significant_tokens("9 de julio") == ["9", "julio"]
    assert significant_tokens("24 de septiembre") == ["24", "septiembre"]


def test_matching_token_set_nueve_julio(catalog_pr6a) -> None:
    assert matching_token_set("nueve de julio") == matching_token_set("9 de julio")


@pytest.mark.parametrize(
    "raw,expected_canon,allowed_strategies",
    [
        ("9 de julio", "9 de Julio", {"exact_nombre", "exact_key", "exact_tokens"}),
        ("9 julio", "9 de Julio", {"exact_tokens", "exact_key"}),
        ("nueve de julio", "9 de Julio", {"exact_tokens", "exact_key", "exact_nombre"}),
        ("24 de septiembre", "24 De Septiembre", {"exact_nombre", "exact_key", "exact_tokens"}),
        ("24 septiembre", "24 De Septiembre", {"exact_tokens", "exact_key"}),
        ("veinticuatro de septiembre", "24 De Septiembre", {"exact_tokens", "exact_key", "exact_nombre"}),
    ],
)
def test_fechas_ok(catalog_pr6a, raw: str, expected_canon: str, allowed_strategies: set[str]) -> None:
    result = match_calle(raw)
    assert result["status"] == "OK", result
    assert result["canon"] == expected_canon
    assert result["match_strategy"] in allowed_strategies


def test_roca_ambiguo_review(catalog_pr6a) -> None:
    result = match_calle("roca")
    assert result["status"] == "REVIEW"
    assert result["match_strategy"] == "token_containment"
    assert len(result["candidates"] or []) >= 2


def test_santiago_ambiguo_review(catalog_pr6a) -> None:
    result = match_calle("santiago")
    assert result["status"] == "REVIEW"
    assert result["match_strategy"] in {"token_containment", "fuzzy"}


def test_match_incluye_confidence_reason(catalog_pr6a) -> None:
    result = match_calle("9 julio")
    assert result.get("confidence_reason")
    assert result.get("match_strategy")
