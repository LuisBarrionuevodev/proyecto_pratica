"""Tests PR4 — matching local de calles (Tucumán)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import pytest

from app.domains.geolocalizacion.normalizacion_calles.services.calle_alias_service import (
    reload_calle_aliases_cache,
    resolve_calle_alias,
)
from app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service import (
    OK_THRESHOLD,
    REVIEW_THRESHOLD,
    match_calle,
)
from app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_match_metrics_service import (
    analyze_street_match_samples,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import (
    normalize_street,
    street_base,
)


@dataclass
class _FakeCalle:
    id: int
    nombre_canonico: str
    nombre_key: str
    canon_base: str
    activo: bool = True


def _catalog_tucuman() -> list[_FakeCalle]:
    from app.domains.geolocalizacion.normalizacion_calles.services.normalize_string import slug_key

    rows = [
        ("Dr Bernardo Monteagudo", "bernardo monteagudo"),
        ("Avenida Fernando Mate de Luna", "fernando mate de luna"),
        ("Santiago del Estero", "santiago del estero"),
        ("San Martin", "san martin"),
        ("Pasaje XYZ", "xyz"),
        ("Avenida Araoz", "araoz"),
        ("Calle Araoz", "araoz"),
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
def catalog(monkeypatch: pytest.MonkeyPatch) -> list[_FakeCalle]:
    rows = _catalog_tucuman()
    reload_calle_aliases_cache()

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


@pytest.mark.parametrize(
    "raw,expected_canon",
    [
        ("monteagudo", "Dr Bernardo Monteagudo"),
        ("b monteagudo", "Dr Bernardo Monteagudo"),
        ("dr monteagudo", "Dr Bernardo Monteagudo"),
        ("bernardo monteagudo", "Dr Bernardo Monteagudo"),
        ("av mate de luna", "Avenida Fernando Mate de Luna"),
        ("mate luna", "Avenida Fernando Mate de Luna"),
        ("sgo del estero", "Santiago del Estero"),
        ("santiago estero", "Santiago del Estero"),
        ("san martin", "San Martin"),
    ],
)
def test_match_calle_casos_tucuman_ok(catalog, raw: str, expected_canon: str) -> None:
    result = match_calle(raw)
    assert result["status"] == "OK", result
    assert result["canon"] == expected_canon
    assert result["catalogo_id"] is not None
    assert float(result["score"] or 0) >= 0.9


def test_pje_xyz_ok_si_existe_en_catalogo(catalog) -> None:
    result = match_calle("pje xyz")
    assert result["status"] == "OK"
    assert result["canon"] == "Pasaje XYZ"


def test_calle_inexistente_no_match(catalog) -> None:
    result = match_calle("calle inventada inexistente 9999")
    assert result["status"] == "NO_MATCH"


def test_dos_candidatas_parecidas_review(catalog) -> None:
    result = match_calle("araoz")
    assert result["status"] == "REVIEW"
    assert result["candidates"]
    assert len(result["candidates"]) >= 2


def test_umbrales_pr4_documentados() -> None:
    assert OK_THRESHOLD == 0.92
    assert REVIEW_THRESHOLD == 0.78


def test_normalize_street_expande_abreviaturas() -> None:
    assert normalize_street("av. mate de luna") == "avenida mate de luna"
    assert normalize_street("dr monteagudo") == "doctor monteagudo"
    assert normalize_street("sgo del estero") == "santiago del estero"


def test_street_base_quita_via_y_titulo() -> None:
    assert street_base("Dr Bernardo Monteagudo") == "bernardo monteagudo"
    assert street_base("Avenida Fernando Mate de Luna") == "fernando mate de luna"


def test_resolve_alias_monteagudo() -> None:
    reload_calle_aliases_cache()
    assert resolve_calle_alias("monteagudo") == "Dr Bernardo Monteagudo"


def test_analyze_street_match_samples(catalog) -> None:
    samples = ["monteagudo", "mate luna", "calle inventada inexistente 9999", "araoz"]
    report = analyze_street_match_samples(samples)
    assert report["total"] == 4
    assert report["ok"] >= 2
    assert report["review"] >= 1
    assert report["no_match"] >= 1
    assert 0.0 <= report["success_rate"] <= 1.0
