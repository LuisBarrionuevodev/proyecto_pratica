"""Validaciones PREDEPLOY-CLEANUP.3C.2 — execution manifest FASE 2B."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.manifest_io import manifest_sha256
from app.domains.predeploy_cleanup.phase2b_routes_manifest_freeze import (
    BASELINE_EXPECTED,
    FORBIDDEN_MANIFEST_ENTITIES,
    PHASE2B_DELETE_ORDER,
    POST_EXPECTED,
    SAFE_SET_KEYS,
    load_safe_sets_from_reconcile,
)

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
RECONCILE = OUTPUT / "cleanup_phase2b_route_items_reconcile_20260920.json"
MANIFEST = OUTPUT / "cleanup_execution_manifest_phase2b_routes_20260920.json"
DRY_RUN_V3 = OUTPUT / "cleanup_phase1_dry_run_v3_20260920_015729.json"


@pytest.fixture
def safe_sets() -> dict[str, set[int]]:
    assert RECONCILE.is_file(), "Ejecutar reconcile 3C.1 primero"
    return load_safe_sets_from_reconcile(RECONCILE)


@pytest.fixture
def manifest() -> dict:
    assert MANIFEST.is_file(), "Ejecutar freeze_cleanup_phase2b_execution_manifest.py primero"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_exact_safe_set_counts(safe_sets: dict) -> None:
    for entity, (_, expected) in SAFE_SET_KEYS.items():
        assert len(safe_sets[entity]) == expected


def test_no_duplicate_ids(safe_sets: dict) -> None:
    for entity, ids in safe_sets.items():
        raw = json.loads(RECONCILE.read_text(encoding="utf-8"))["safe_sets"]
        key = SAFE_SET_KEYS[entity][0]
        assert len(ids) == len(raw[key])


def test_manifest_writes_not_executed(manifest: dict) -> None:
    assert manifest["writes_executed"] is False
    assert manifest["phase"] == "2B"


def test_manifest_entity_counts(manifest: dict) -> None:
    for entity in PHASE2B_DELETE_ORDER:
        assert len(manifest["entities"][entity]) == SAFE_SET_KEYS[entity][1]


def test_delete_order_valid(manifest: dict) -> None:
    assert manifest["delete_order"] == PHASE2B_DELETE_ORDER
    assert manifest["validation"]["delete_order_validated"]["valid"] is True


def test_post_count_arithmetic(manifest: dict) -> None:
    for entity in PHASE2B_DELETE_ORDER:
        before = manifest["expected_counts_before"][entity]
        after = manifest["expected_counts_after"][entity]
        delete_n = len(manifest["entities"][entity])
        assert before - delete_n == after
        assert after == POST_EXPECTED[entity]


def test_baseline_unchanged_entities(manifest: dict) -> None:
    for key, expected in BASELINE_EXPECTED.items():
        if key in PHASE2B_DELETE_ORDER:
            continue
        assert manifest["unchanged_entities"][key] == expected


def test_all_ids_exist_report(manifest: dict) -> None:
    ids_report = manifest["validation"]["ids_exist"]
    for entity in PHASE2B_DELETE_ORDER:
        assert ids_report[entity]["missing"] == 0
        assert ids_report[entity]["found"] == ids_report[entity]["expected"]


def test_iniciadores_no_surviving_refs(manifest: dict) -> None:
    ini = manifest["validation"]["iniciador_refs"]
    assert ini["all_zero_refs_after_sim"] is True
    assert ini["iniciadores_checked"] == 369


def test_empty_groups_post_sim(manifest: dict) -> None:
    assert manifest["validation"]["empty_groups"]["all_empty_after_sim"] is True


def test_empty_routes_post_sim(manifest: dict) -> None:
    assert manifest["validation"]["empty_routes"]["all_empty_after_sim"] is True


def test_protected_closure_zero(manifest: dict) -> None:
    assert manifest["protected_intersection"] == 0
    assert manifest["validation"]["protected_closure"]["valid"] is True


def test_no_protected_wrapper_in_safe_ini(manifest: dict) -> None:
    v3 = json.loads(DRY_RUN_V3.read_text(encoding="utf-8"))
    protected = set(
        v3["iniciador_wrapper_incorporated"]["protected_from_wrappers_64"]
    )
    safe_ini = {e["id"] for e in manifest["entities"]["iniciador_ruta"]}
    assert not (safe_ini & protected)


def test_forbidden_entities_not_in_manifest(manifest: dict) -> None:
    assert set(manifest["entities"].keys()) == set(PHASE2B_DELETE_ORDER)
    for forbidden in FORBIDDEN_MANIFEST_ENTITIES:
        assert forbidden not in manifest["entities"]
        assert manifest["forbidden_deletes"].get(forbidden, 0) == 0


def test_unlock_expectations(manifest: dict) -> None:
    unlock = manifest["unlock_expectations"]
    assert unlock["denuncias_test"]["UNLOCKED_FOR_PHASE2C"] == 75
    assert unlock["denuncias_test"]["delete_in_2b"] == 0
    assert unlock["actuaciones_test"]["UNLOCKED_AFTER_2B"] == 265
    assert unlock["relevamientos_test"]["UNLOCKED_AFTER_2B"] == 0
    qa = unlock["relevamientos_test"]["qa_focus_status"]
    for rid in (4811, 4812, 4816, 4860, 4861):
        assert (qa.get(rid) or qa.get(str(rid))) == "STILL_BLOCKED"


def test_wrapper64_metadata(manifest: dict) -> None:
    w = manifest["wrapper64_metadata"]
    assert w["wrapper_records"] == 64
    assert w["unique_iniciadores"] == 63
    assert w["deletable_count"] == 36
    assert w["protected_count"] == 27
    assert w["protected_leaked_into_safe_ini"] == 0


def test_manifest_sha256_stable(manifest: dict) -> None:
    stored = manifest["manifest_sha256"]
    assert stored == manifest_sha256(manifest)
