"""Validaciones PREDEPLOY-CLEANUP.3A.3 — reconciliación EO FASE 2A."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.phase2a_eo_reconcile import load_eo_sets

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
BLOCKERS = OUTPUT / "cleanup_phase2_blockers_diag_20260920.json"
INDET = OUTPUT / "cleanup_phase2_eo_indeterminate_diag_20260920.json"
STRUCTURED = OUTPUT / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
RECONCILE = OUTPUT / "cleanup_phase2a_eo_reconcile_20260920.json"
MANIFEST = OUTPUT / "cleanup_execution_manifest_phase2a_eo_20260920.json"


@pytest.fixture
def sets_info() -> dict:
    assert BLOCKERS.is_file() and INDET.is_file() and STRUCTURED.is_file()
    return load_eo_sets(BLOCKERS, INDET, STRUCTURED)


def test_sets_disjoint_union_400(sets_info: dict) -> None:
    a, b, c = set(sets_info["SET_A"]), set(sets_info["SET_B"]), set(sets_info["SET_C"])
    assert len(a) == 77
    assert len(b) == 62
    assert len(c) == 261
    assert not (a & b)
    assert not (a & c)
    assert not (b & c)
    assert len(sets_info["SAFE_EO_FINAL"]) == 400
    assert sets_info["arithmetic_check"]["disjoint"] is True


def test_reconcile_report_exists_and_valid() -> None:
    assert RECONCILE.is_file(), "Ejecutar diag_cleanup_phase2a_eo_reconcile.py primero"
    report = json.loads(RECONCILE.read_text(encoding="utf-8"))
    assert report["writes_executed"] is False
    rev = report["revalidation"]
    assert rev["degraded_count"] == 0
    assert rev["missing_ids"] == []
    assert rev["phase2a_set_null_allowed"] is True
    assert rev["set_null_by_classification"]["PROTECTED_REAL"] == 0
    assert rev["set_null_by_classification"]["INDETERMINADO"] == 0


def test_manifest_proposal_eo_only() -> None:
    assert MANIFEST.is_file()
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["writes_executed"] is False
    assert m["phase"] == "2A"
    assert list(m["entities"].keys()) == ["establecimiento_operativo"]
    assert len(m["entities"]["establecimiento_operativo"]) == 400
    assert m["validation"]["forbidden_deletes"]["domicilio"] == 0
    assert m["validation"]["forbidden_deletes"]["actuaciones"] == 0
    assert m["validation"]["forbidden_deletes"]["users"] == 0
    assert m["post_estimated"]["establecimiento_operativo"] == 2057 - 400


def test_sets_preserve_ids(sets_info: dict) -> None:
    """Ningún set pierde IDs al serializar."""
    for key in ("SET_A", "SET_B", "SET_C", "SAFE_EO_FINAL"):
        ids = sets_info[key]
        assert len(ids) == len(set(ids))
        assert all(isinstance(i, int) for i in ids)
