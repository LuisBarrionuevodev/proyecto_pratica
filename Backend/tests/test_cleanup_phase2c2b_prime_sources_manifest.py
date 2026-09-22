"""Validaciones PREDEPLOY-CLEANUP.3H.3 — execution manifest FASE 2C.2B'."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.manifest_io import manifest_sha256
from app.domains.predeploy_cleanup.phase2c2b_prime_sources_manifest_freeze import (
    BASELINE_POST_2C2A_PRIME,
    EMPTY_ROUTE_IDS,
    EXPECTED_ACTS,
    EXPECTED_CASCADE_PHYSICAL,
    EXPECTED_OLD,
    EXPECTED_OT,
    EXPECTED_STRUCTURED,
    FORBIDDEN_MANIFEST_ENTITIES,
    PHASE2C2B_PRIME_DELETE_ORDER,
    POST_EXPLICIT,
    load_safe_sets_from_apply_report,
)
from app.domains.predeploy_cleanup.phase2c2_notification_source_diag import PROTECTED_COMP_CLOSURE_8

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
APPLY_2C2A_PRIME = OUTPUT / "cleanup_phase2c2a_prime_wrappers_apply_20260920_154757.json"
MANIFEST = OUTPUT / "cleanup_execution_manifest_phase2c2b_prime_sources_20260920.json"


@pytest.fixture
def safe_sets() -> dict:
    assert APPLY_2C2A_PRIME.is_file(), "Ejecutar apply 3H.2 primero"
    return load_safe_sets_from_apply_report(APPLY_2C2A_PRIME)


@pytest.fixture
def manifest() -> dict:
    assert MANIFEST.is_file(), "Ejecutar freeze_cleanup_phase2c2b_prime_execution_manifest.py primero"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_exact_safe_counts(safe_sets: dict) -> None:
    assert len(safe_sets["actuaciones"]) == EXPECTED_ACTS
    assert len(safe_sets["orden_trabajo"]) == EXPECTED_OT


def test_family_old_38_structured_0(manifest: dict) -> None:
    fam = manifest["act_family_breakdown"]
    assert fam["SET_ACT_OLD_count"] == EXPECTED_OLD
    assert fam["SET_ACT_STRUCTURED_count"] == EXPECTED_STRUCTURED


def test_manifest_phase_and_entities(manifest: dict) -> None:
    assert manifest["phase"] == "2C2B_PRIME"
    assert manifest["writes_executed"] is False
    assert len(manifest["entities"]["actuaciones"]) == EXPECTED_ACTS
    assert len(manifest["entities"]["orden_trabajo"]) == EXPECTED_OT


def test_all_ids_exist_no_duplicates(manifest: dict) -> None:
    for entity in PHASE2C2B_PRIME_DELETE_ORDER:
        ids = manifest["entities"][entity]
        assert manifest["validation"]["ids_exist"][entity]["missing"] == 0
        assert len(ids) == len(set(ids))


def test_act_blockers_zero(manifest: dict) -> None:
    assert manifest["validation"]["act_blockers_zero"] is True


def test_ot_exclusive(manifest: dict) -> None:
    assert manifest["validation"]["ot_exclusive"]["all_exclusive_to_safe_acts"] is True


def test_protected_closure_zero(manifest: dict) -> None:
    assert manifest["protected_intersection"] == 0
    assert manifest["protected_closure_detail"]["valid"] is True


def test_cascade_physical_zero(manifest: dict) -> None:
    assert manifest["validation"]["cascade_physical_total"] == 0
    for tbl, spec in EXPECTED_CASCADE_PHYSICAL.items():
        assert manifest["expected_cascades"][tbl]["physical_rows"] == spec["physical_rows"]


def test_parent_docs_preserved_not_deleted(manifest: dict) -> None:
    assert "notificacion" not in manifest["entities"]
    assert "comprobacion" not in manifest["entities"]
    pd = manifest["preserve_parent_documents"]
    assert pd["preserve_policy"] == "NO_DELETE_NO_UPDATE"
    assert len(pd["notificacion_ids"]) > 0 or len(pd["comprobacion_ids"]) > 0


def test_source_docs_excluded(manifest: dict) -> None:
    sd = manifest["preserve_source_documents"]
    assert len(sd["direct_notificaciones_29"]) == 29
    assert len(sd["source_notificaciones_119"]) == 119


def test_future_orphan_from_db(manifest: dict) -> None:
    fo = manifest["future_orphan_documents_after_apply"]
    assert len(fo["NEW_ORPHAN_NOTIFICACION_AFTER_2C2B_PRIME"]) == 25
    assert fo["NEW_ORPHAN_COMPROBACION_AFTER_2C2B_PRIME"] == [2289]


def test_existing_orphan_docs_excluded(manifest: dict) -> None:
    assert len(manifest["excluded"]["orphan_notificaciones_36"]) == 36
    assert len(manifest["excluded"]["orphan_comprobaciones_20"]) == 20


def test_empty_routes_excluded(manifest: dict) -> None:
    assert len(manifest["empty_routes_residual_12"]) == 12
    assert manifest["excluded"]["empty_routes_12"] == list(EMPTY_ROUTE_IDS)
    for r in manifest["empty_routes_residual_12"]:
        assert r["ruta_item_refs"] == 0


def test_protected_comprobacion_8_regression(manifest: dict) -> None:
    reg = manifest["protected_comprobacion_regression"]
    assert reg["all_protected"] is True
    assert set(reg["closure_8_ids"]) == set(PROTECTED_COMP_CLOSURE_8)


def test_post_count_actuaciones(manifest: dict) -> None:
    before = manifest["expected_counts_before"]["actuaciones"]
    after = manifest["expected_counts_after"]["actuaciones"]
    assert before == BASELINE_POST_2C2A_PRIME["actuaciones"]
    assert before - EXPECTED_ACTS == after
    assert after == POST_EXPLICIT["actuaciones"]


def test_post_count_ot(manifest: dict) -> None:
    before = manifest["expected_counts_before"]["orden_trabajo"]
    after = manifest["expected_counts_after"]["orden_trabajo"]
    assert before - EXPECTED_OT == after
    assert after == POST_EXPLICIT["orden_trabajo"]


def test_other_hard_counts_unchanged(manifest: dict) -> None:
    for key, expected in BASELINE_POST_2C2A_PRIME.items():
        if key in POST_EXPLICIT:
            continue
        assert manifest["unchanged_counts"][key] == expected


def test_forbidden_entities_not_in_manifest(manifest: dict) -> None:
    assert set(manifest["entities"].keys()) == set(PHASE2C2B_PRIME_DELETE_ORDER)
    for forbidden in FORBIDDEN_MANIFEST_ENTITIES:
        assert forbidden not in manifest["entities"]


def test_delete_order_valid(manifest: dict) -> None:
    assert manifest["delete_order"] == PHASE2C2B_PRIME_DELETE_ORDER
    assert manifest["validation"]["delete_order_validated"]["valid"] is True


def test_manifest_sha256_stable(manifest: dict) -> None:
    assert manifest["manifest_sha256"] == manifest_sha256(manifest)
