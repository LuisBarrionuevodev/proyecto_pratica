"""Validaciones PREDEPLOY-CLEANUP.3E.1 — execution manifest FASE 2C.1."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.manifest_io import manifest_sha256
from app.domains.predeploy_cleanup.phase2c1_sources_manifest_freeze import (
    EXPECTED_CASCADE_COUNTS,
    FORBIDDEN_MANIFEST_ENTITIES,
    PHASE2C1_DELETE_ORDER,
    POST_EXPECTED,
    SAFE_SET_SPECS,
    load_safe_sets_from_diag,
)

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
DIAG = OUTPUT / "cleanup_phase2c1_unlocked_sources_diag_20260920.json"
MANIFEST = OUTPUT / "cleanup_execution_manifest_phase2c1_sources_20260920.json"


@pytest.fixture
def safe_sets() -> dict:
    assert DIAG.is_file(), "Ejecutar diag 3E primero"
    return load_safe_sets_from_diag(DIAG)


@pytest.fixture
def manifest() -> dict:
    assert MANIFEST.is_file(), "Ejecutar freeze_cleanup_phase2c1_execution_manifest.py primero"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_exact_safe_set_counts(safe_sets: dict) -> None:
    for entity, (_, expected) in SAFE_SET_SPECS.items():
        assert len(safe_sets[entity]) == expected


def test_manifest_entity_counts(manifest: dict) -> None:
    assert manifest["phase"] == "2C1"
    assert manifest["writes_executed"] is False
    for entity in PHASE2C1_DELETE_ORDER:
        assert len(manifest["entities"][entity]) == SAFE_SET_SPECS[entity][1]


def test_all_ids_exist(manifest: dict) -> None:
    for entity in PHASE2C1_DELETE_ORDER:
        report = manifest["validation"]["ids_exist"][entity]
        assert report["missing"] == 0


def test_act_routing_blockers_zero(manifest: dict) -> None:
    assert manifest["validation"]["act_routing_blockers"]["all_zero_refs"] is True


def test_den_routing_blockers_zero(manifest: dict) -> None:
    assert manifest["validation"]["den_routing_blockers"]["all_zero_refs"] is True


def test_ot_exclusive(manifest: dict) -> None:
    assert manifest["validation"]["ot_exclusive"]["all_exclusive_to_safe_acts"] is True


def test_expected_cascades_exact(manifest: dict) -> None:
    for tbl, expected in EXPECTED_CASCADE_COUNTS.items():
        assert manifest["expected_cascades"][tbl]["count"] == expected


def test_notificacion_comprobacion_not_deleted(manifest: dict) -> None:
    assert "notificacion" not in manifest["entities"]
    assert "comprobacion" not in manifest["entities"]
    assert manifest["forbidden_deletes"]["notificacion"] == 0
    assert manifest["forbidden_deletes"]["comprobacion"] == 0
    assert "preserve_document_refs" in manifest


def test_forbidden_entities_not_in_manifest(manifest: dict) -> None:
    assert set(manifest["entities"].keys()) == set(PHASE2C1_DELETE_ORDER)
    for forbidden in FORBIDDEN_MANIFEST_ENTITIES:
        assert forbidden not in manifest["entities"]


def test_blocked_acts_intersection_zero(manifest: dict) -> None:
    assert manifest["validation"]["excluded"]["blocked_acts_manifest_intersection"] == 0


def test_relevamientos_intersection_zero(manifest: dict) -> None:
    assert manifest["validation"]["excluded"]["relevamientos_manifest_intersection"] == 0


def test_protected_closure_zero(manifest: dict) -> None:
    assert manifest["protected_intersection"] == 0
    assert manifest["validation"]["protected_closure"]["valid"] is True


def test_delete_order_valid(manifest: dict) -> None:
    assert manifest["delete_order"] == PHASE2C1_DELETE_ORDER
    assert manifest["validation"]["delete_order_validated"]["valid"] is True


def test_post_count_arithmetic(manifest: dict) -> None:
    for entity in PHASE2C1_DELETE_ORDER:
        before = manifest["expected_counts_before"][entity]
        after = manifest["expected_counts_after"][entity]
        delete_n = len(manifest["entities"][entity])
        assert before - delete_n == after
        assert after == POST_EXPECTED[entity]


def test_act_family_structured_only(manifest: dict) -> None:
    fam = manifest["validation"]["act_family"]
    assert fam["all_SET_ACT_STRUCTURED"] is True
    assert fam["SET_ACT_OLD_in_set"] == 0


def test_manifest_sha256_stable(manifest: dict) -> None:
    assert manifest["manifest_sha256"] == manifest_sha256(manifest)
