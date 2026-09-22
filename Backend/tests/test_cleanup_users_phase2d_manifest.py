"""Validaciones PREDEPLOY-CLEANUP.3L.1 — execution manifest FASE 2D USERS."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.manifest_io import manifest_sha256
from app.domains.predeploy_cleanup.users_phase2d_manifest_freeze import (
    CLASSIFICATION_EXPECTED,
    EXPECTED_BLOCKED,
    EXPECTED_SAFE,
    EXPECTED_USERS_AFTER,
    EXPECTED_USERS_TOTAL,
    PRESERVE_USER_IDS,
    REAL_USER_IDS,
    SYSTEM_USER_IDS,
    load_diag_for_freeze,
)

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
DIAG_3L = OUTPUT / "cleanup_users_phase2d_diag_20260920.json"
MANIFEST = OUTPUT / "cleanup_execution_manifest_users_phase2d_20260920.json"


@pytest.fixture
def diag_data() -> dict:
    assert DIAG_3L.is_file(), "Ejecutar diag 3L primero"
    return load_diag_for_freeze(DIAG_3L)


@pytest.fixture
def manifest() -> dict:
    assert MANIFEST.is_file(), "Ejecutar freeze_cleanup_users_phase2d_execution_manifest.py primero"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_safe_users_count_833(diag_data: dict) -> None:
    assert len(diag_data["safe_users"]["SAFE_USERS_2D"]) == EXPECTED_SAFE


def test_exact_safe_ids_from_diag(diag_data: dict, manifest: dict) -> None:
    diag_ids = diag_data["safe_users"]["SAFE_USERS_2D"]
    manifest_ids = manifest["entities"]["users"]
    assert diag_ids == manifest_ids
    assert len(manifest_ids) == EXPECTED_SAFE


def test_all_safe_exist_no_duplicates(manifest: dict) -> None:
    ids = manifest["entities"]["users"]
    assert manifest["validation"]["safe_ids_exist"] is True
    assert len(ids) == len(set(ids))


def test_safe_classification_fk_free(manifest: dict) -> None:
    assert manifest["classification"]["safe_confirmado_test_fk_free"] == EXPECTED_SAFE
    for row in manifest["identity_snapshot"]:
        assert row["classification"] == "CONFIRMADO_TEST_FK_FREE"
        assert row["test_provenance_conclusive"] is True
        assert row["whitelist"] is False
        assert row["system_admin_preserve"] is False


def test_safe_fk_refs_zero(manifest: dict) -> None:
    fk_val = manifest["fk_validation"]
    assert fk_val["total_refs"] == 0
    assert fk_val["restrict_refs"] == 0
    assert fk_val["cascade_refs"] == 0
    assert fk_val["set_null_refs"] == 0
    assert fk_val["valid"] is True


def test_safe_auth_children_zero(manifest: dict) -> None:
    fk_val = manifest["fk_validation"]
    assert fk_val["profiles_safe_refs"] == 0
    assert fk_val["password_reset_codes_safe_refs"] == 0


def test_expected_effects_zero_cascade(manifest: dict) -> None:
    eff = manifest["expected_effects"]
    assert eff["explicit_delete_users"] == EXPECTED_SAFE
    assert eff["cascade"] == 0
    assert eff["set_null"] == 0
    assert eff["restrict"] == 0


def test_active_distribution(manifest: dict) -> None:
    assert manifest["active_status_safe"]["active_true"] == EXPECTED_SAFE
    assert manifest["active_status_safe"]["active_false"] == 0


def test_user1_excluded(manifest: dict) -> None:
    safe = set(manifest["entities"]["users"])
    assert 1 not in safe
    assert manifest["preserve"]["system_user_ids"] == [1]
    assert manifest["user1_guard"]["user_id"] == 1
    assert manifest["user1_guard"]["no_delete"] is True


def test_real_ids_excluded(manifest: dict) -> None:
    safe = set(manifest["entities"]["users"])
    assert safe.isdisjoint(REAL_USER_IDS)
    assert set(manifest["preserve"]["real_user_ids"]) == set(REAL_USER_IDS)


def test_preserve_total_14(manifest: dict) -> None:
    assert len(PRESERVE_USER_IDS) == 14
    assert SYSTEM_USER_IDS | REAL_USER_IDS == PRESERVE_USER_IDS


def test_blocked_test_users_1956(manifest: dict) -> None:
    blocked = manifest["preserve"]["blocked_test_user_ids"]
    assert len(blocked) == EXPECTED_BLOCKED
    assert len(blocked) == len(set(blocked))


def test_safe_disjoint_sets(manifest: dict) -> None:
    safe = set(manifest["entities"]["users"])
    blocked = set(manifest["preserve"]["blocked_test_user_ids"])
    assert safe.isdisjoint(blocked)
    assert safe.isdisjoint(REAL_USER_IDS)
    assert safe.isdisjoint(SYSTEM_USER_IDS)


def test_classification_total_2803(manifest: dict) -> None:
    summary = manifest["classification"]["summary"]
    assert summary == CLASSIFICATION_EXPECTED
    assert sum(summary.values()) == EXPECTED_USERS_TOTAL


def test_expected_users_post_1970(manifest: dict) -> None:
    assert manifest["expected_users_after"] == EXPECTED_USERS_AFTER
    assert manifest["expected_counts_after"]["users"] == EXPECTED_USERS_AFTER


def test_survivor_reconciliation(manifest: dict) -> None:
    rec = manifest["survivor_reconciliation"]
    assert rec["blocked_test"] == EXPECTED_BLOCKED
    assert rec["real"] == 13
    assert rec["system"] == 1
    assert rec["total"] == EXPECTED_USERS_AFTER
    assert rec["blocked_test"] + rec["real"] + rec["system"] == EXPECTED_USERS_AFTER


def test_profiles_and_password_reset_unchanged(manifest: dict) -> None:
    before = manifest["expected_counts_before"]
    after = manifest["expected_counts_after"]
    assert before["profiles"] == 7
    assert after["profiles"] == 7
    assert before["password_reset_codes"] == 1
    assert after["password_reset_codes"] == 1


def test_protected_intersection_zero(manifest: dict) -> None:
    assert manifest["protected_intersection"] == 0
    assert manifest["protected_closure_detail"]["valid"] is True


def test_known_test_guards(manifest: dict) -> None:
    guards = manifest["known_test_operational_guards"]
    assert guards["known_test_acts_remaining"] == 0
    assert guards["known_test_ot_remaining"] == 0
    assert guards["route_residual_safe_remaining"] == 0
    assert guards["admin_graph_safe_remaining"] == 0
    assert guards["guard_ok"] is True


def test_juzgado_922_guard(manifest: dict) -> None:
    jz = manifest["juzgado_922_guard"]
    assert jz["juzgado_id"] == 922
    assert jz["exists"] is True
    assert jz["fk_refs_current"] == 0
    assert jz["status"] == "READY_FOR_PHASE2E"
    assert jz["no_delete_in_2d"] is True


def test_identity_snapshot_hash_stable(manifest: dict) -> None:
    assert manifest["identity_snapshot_hash"]
    assert len(manifest["identity_snapshot"]) == EXPECTED_SAFE
    for row in manifest["identity_snapshot"]:
        assert row["identity_fingerprint"]


def test_manifest_hash_stable(manifest: dict) -> None:
    stored = manifest["manifest_sha256"]
    computed = manifest_sha256(manifest)
    assert stored == computed


def test_writes_executed_false(manifest: dict) -> None:
    assert manifest["writes_executed"] is False
    assert manifest["phase"] == "2D_USERS"
