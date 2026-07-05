"""Tests PR5 — diagnóstico nomenclatura pendiente y sugerencia de alias."""

from __future__ import annotations

import csv
import random
from pathlib import Path
from unittest.mock import patch

import pytest

from app.database import db
from app.domains.geolocalizacion.normalizacion_calles.services.calle_alias_service import (
    reload_calle_aliases_cache,
    resolve_calle_alias,
)
from app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_pendiente_diagnosis_service import (
    append_suggested_aliases_to_csv,
    diagnose_pendiente_nomenclatura,
    fetch_pendiente_calle_frecuencias,
    simulate_rematch_for_samples,
    suggest_aliases_from_simulation,
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


def test_simulate_rematch_counts_ok_domicilios() -> None:
    samples = [
        {"text": "monteagudo", "count": 3, "statuses": {"PENDIENTE": 3}},
        {"text": "xyz desconocida", "count": 1, "statuses": {"NO_MATCH": 1}},
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


def test_suggest_aliases_skips_ok_and_existing_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    reload_calle_aliases_cache()
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_pendiente_diagnosis_service.resolve_calle_alias",
        lambda text: "Dr Bernardo Monteagudo" if text.lower() == "monteagudo" else None,
    )

    simulation = {
        "details": [
            {
                "text": "monteagudo",
                "count": 5,
                "simulated_status": "OK",
                "top_candidate": {"display": "Dr Bernardo Monteagudo", "score": 1.0},
            },
            {
                "text": "av avellaneda",
                "count": 4,
                "simulated_status": "REVIEW",
                "top_candidate": {"display": "Dr M de Avellaneda", "score": 0.98},
            },
            {
                "text": "calle rara",
                "count": 3,
                "simulated_status": "NO_MATCH",
                "top_candidate": {"display": "Otra", "score": 0.6},
            },
        ]
    }

    suggestions = suggest_aliases_from_simulation(simulation, min_count=2, min_score=0.78)
    assert len(suggestions) == 1
    assert suggestions[0]["alias"] == "av avellaneda"
    assert suggestions[0]["nombre_canonico"] == "Dr M de Avellaneda"


def test_append_suggested_aliases_dry_run_and_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    csv_path = tmp_path / "calle_aliases.csv"
    csv_path.write_text("alias,nombre_canonico,notas\nsan martin,San Martin,existente\n", encoding="utf-8")
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_pendiente_diagnosis_service._ALIASES_CSV",
        csv_path,
    )

    suggestions = [
        {"alias": "san martin", "nombre_canonico": "San Martin", "notas": "dup"},
        {"alias": "av avellaneda", "nombre_canonico": "Dr M de Avellaneda", "notas": "nuevo"},
    ]

    dry = append_suggested_aliases_to_csv(suggestions, dry_run=True)
    assert dry["added"] == 1
    assert dry["skipped_existing"] == 1
    assert len(list(csv.DictReader(csv_path.open(encoding="utf-8")))) == 1

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
    by_text = {r["text"]: r["count"] for r in rows}
    assert by_text.get(calle_a) == 3
    assert by_text.get(calle_b) == 1


def test_diagnose_pendiente_nomenclatura_shape(app_ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    calle = _unique_calle("PR5Diag")
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
    assert "domicilios_pendientes_total" in report
    assert "simulation" in report
    assert "suggested_aliases" in report
    assert "impact_estimate" in report
    assert report["unique_calle_groups_analyzed"] >= 1


def test_av_avellaneda_alias_resolves_after_pr5_csv() -> None:
    reload_calle_aliases_cache()
    assert resolve_calle_alias("av avellaneda") == "Dr M de Avellaneda"
