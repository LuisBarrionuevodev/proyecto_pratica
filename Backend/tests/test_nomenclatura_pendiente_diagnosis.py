"""Tests PR5/PR5b — diagnóstico nomenclatura pendiente y sugerencia de alias."""

from __future__ import annotations

import csv
import random
from pathlib import Path
from unittest.mock import patch

import pytest

from app.database import db
from app.domains.geolocalizacion.normalizacion_calles.services.calle_alias_service import (
    audit_calle_aliases,
    reload_calle_aliases_cache,
    resolve_calle_alias,
)
from app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_pendiente_diagnosis_service import (
    append_suggested_aliases_to_csv,
    diagnose_pendiente_nomenclatura,
    fetch_pendiente_calle_frecuencias,
    is_synthetic_calle_text,
    simulate_rematch_for_samples,
    suggest_aliases_from_simulation,
    top_real_no_match_candidates,
)
from app.models import Domicilio


def _unique_calle(prefix: str) -> str:
    return f"{prefix}{random.randint(0, 999999)}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def test_is_synthetic_calle_text() -> None:
    synthetic = [
        "CalleMotor",
        "CalleProrroga",
        "EditPerm",
        "EditPlazo",
        "PresenterPlazo",
        "ReactivaOficio",
        "PR3Oficios",
        "PR5FreqA995565",
        "ActNew-b8edca04",
        "ActOld-9f3a2098",
        "DenPR2-dd2c04b6",
        "CSoloEnv307788",
        "CReinB545225",
        "UGB834503",
        "UGA123456",
        "HotfixNot855487",
        "ReencCalle_abc123",
        "RelGeo_a1b2c3d4",
        "RelGeoPres_xyz",
        "CEd834503",
        "Stab10Den123",
        "St4_deadbeef",
    ]
    for sample in synthetic:
        assert is_synthetic_calle_text(sample), sample

    real = [
        "av avellaneda",
        "Santiago del Estero",
        "Av. Ejercito del Norte",
        "Santiago",
        "Cedro",
        "San Martin",
    ]
    for sample in real:
        assert not is_synthetic_calle_text(sample), sample


def test_simulate_rematch_counts_ok_domicilios() -> None:
    samples = [
        {"text": "monteagudo", "count": 3, "statuses": {"PENDIENTE": 3}, "is_synthetic": False},
        {"text": "xyz desconocida", "count": 1, "statuses": {"NO_MATCH": 1}, "is_synthetic": False},
    ]

    def _fake_match(text: str) -> dict:
        if text == "monteagudo":
            return {"status": "OK", "canon": "Dr Bernardo Monteagudo", "score": 1.0, "candidates": []}
        return {
            "status": "NO_MATCH",
            "candidates": [{"display": "Calle X", "score": 0.5}],
        }

    with patch(
        "app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_pendiente_diagnosis_service.match_calle",
        side_effect=_fake_match,
    ):
        result = simulate_rematch_for_samples(samples)

    assert result["would_become_ok_domicilios"] == 3
    assert result["simulated_status_breakdown"]["OK"] == 3
    assert result["simulated_status_breakdown"]["NO_MATCH"] == 1
    assert result["simulated_ok_rate"] == 0.75


def test_suggest_aliases_skips_synthetic_and_invalid_canon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_pendiente_diagnosis_service.resolve_calle_alias",
        lambda text: None,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_pendiente_diagnosis_service.get_by_nombre_canonico",
        lambda canon: object() if canon == "Dr M de Avellaneda" else None,
    )

    simulation = {
        "details": [
            {
                "text": "CalleMotor",
                "count": 100,
                "is_synthetic": True,
                "simulated_status": "NO_MATCH",
                "top_candidate": {"display": "Dr M de Avellaneda", "score": 0.98},
            },
            {
                "text": "av avellaneda",
                "count": 4,
                "is_synthetic": False,
                "simulated_status": "REVIEW",
                "top_candidate": {"display": "Dr M de Avellaneda", "score": 0.98},
            },
            {
                "text": "calle rara",
                "count": 3,
                "is_synthetic": False,
                "simulated_status": "NO_MATCH",
                "top_candidate": {"display": "Inventada", "score": 0.9},
            },
        ]
    }

    suggestions = suggest_aliases_from_simulation(simulation, min_count=2, min_score=0.78)
    assert len(suggestions) == 1
    assert suggestions[0]["alias"] == "av avellaneda"


def test_top_real_no_match_excludes_synthetic() -> None:
    simulation = {
        "details": [
            {"text": "CalleMotor", "count": 50, "is_synthetic": True, "simulated_status": "NO_MATCH"},
            {"text": "Calle Real", "count": 2, "is_synthetic": False, "simulated_status": "NO_MATCH"},
        ]
    }
    top = top_real_no_match_candidates(simulation)
    assert len(top) == 1
    assert top[0]["text"] == "Calle Real"


def test_append_suggested_aliases_validates_canon(app_ctx, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    csv_path = tmp_path / "calle_aliases.csv"
    csv_path.write_text("alias,nombre_canonico,notas\nsan martin,San Martin,existente\n", encoding="utf-8")
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_pendiente_diagnosis_service._ALIASES_CSV",
        csv_path,
    )

    def _canon(name: str):
        if name == "San Martin":
            return type("Row", (), {"nombre_canonico": "San Martin"})()
        if name == "Dr M de Avellaneda":
            return type("Row", (), {"nombre_canonico": "Dr M de Avellaneda"})()
        return None

    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_pendiente_diagnosis_service.get_by_nombre_canonico",
        _canon,
    )

    suggestions = [
        {"alias": "san martin", "nombre_canonico": "San Martin", "notas": "dup"},
        {"alias": "av avellaneda", "nombre_canonico": "Dr M de Avellaneda", "notas": "nuevo"},
        {"alias": "bad alias", "nombre_canonico": "No Existe", "notas": "invalido"},
    ]

    dry = append_suggested_aliases_to_csv(suggestions, dry_run=True)
    assert dry["added"] == 1
    assert dry["skipped_existing"] == 1
    assert dry["skipped_invalid_canon"] == 1

    written = append_suggested_aliases_to_csv(suggestions, dry_run=False)
    assert written["added"] == 1
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    assert len(rows) == 2
    assert rows[-1]["alias"] == "av avellaneda"


def test_fetch_pendiente_calle_frecuencias(app_ctx) -> None:
    calle_a = _unique_calle("PR5FreqA")
    calle_b = _unique_calle("PR5FreqB")
    for _ in range(3):
        db.session.add(
            Domicilio(
                calle=calle_a,
                numero="10",
                calle_norm_status="PENDIENTE",
            )
        )
    db.session.add(
        Domicilio(
            calle=calle_b,
            numero="20",
            calle_norm_status="NO_MATCH",
        )
    )
    db.session.commit()

    rows = fetch_pendiente_calle_frecuencias(limit=500)
    by_text = {r["text"]: r for r in rows}
    assert by_text[calle_a]["count"] == 3
    assert by_text[calle_a]["is_synthetic"] is True
    assert by_text[calle_b]["count"] == 1


def test_diagnose_pendiente_nomenclatura_pr5b_shape(app_ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    calle = _unique_calle("RealCalle")
    db.session.add(
        Domicilio(
            calle=calle,
            numero="99",
            calle_norm_status="REVIEW",
        )
    )
    db.session.commit()

    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_pendiente_diagnosis_service.match_calle",
        lambda text: {
            "status": "REVIEW",
            "score": 0.8,
            "candidates": [{"display": "Canon Test", "score": 0.8}],
        },
    )

    report = diagnose_pendiente_nomenclatura(limit=50)
    assert report["fuente_oficial"] == "calle_catalogo (DB)"
    assert "alias_audit" in report
    assert "origin_split" in report
    assert "match_on_real_texts" in report
    assert "top_real_no_match" in report
    assert report["unique_calle_groups_analyzed"] >= 1


def test_audit_calle_aliases_reports_invalid(app_ctx, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    csv_path = tmp_path / "calle_aliases.csv"
    csv_path.write_text(
        "alias,nombre_canonico,notas\n"
        "ok alias,Dr M de Avellaneda,bien\n"
        "bad alias,Calles Que No Existe,mal\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.calle_alias_service._ALIASES_CSV",
        csv_path,
    )
    reload_calle_aliases_cache()

    def _canon(name: str):
        if name == "Dr M de Avellaneda":
            return type("Row", (), {"id": 1, "nombre_canonico": name})()
        return None

    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.calle_alias_service.get_by_nombre_canonico",
        _canon,
    )
    reload_calle_aliases_cache()

    audit = audit_calle_aliases()
    assert audit["valid_count"] == 1
    assert audit["invalid_count"] == 1
    assert audit["invalid"][0]["alias"] == "bad alias"


def test_av_avellaneda_alias_resolves_with_catalog(app_ctx) -> None:
    reload_calle_aliases_cache()
    assert resolve_calle_alias("av avellaneda") == "Dr M de Avellaneda"
