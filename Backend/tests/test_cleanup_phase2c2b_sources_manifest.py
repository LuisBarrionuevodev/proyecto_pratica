"""Validaciones PREDEPLOY-CLEANUP.3G.1 — execution manifest FASE 2C.2B."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.manifest_io import manifest_sha256
from app.domains.predeploy_cleanup.phase2c2b_sources_manifest_freeze import (
    EXPECTED_ACTS,
    EXPECTED_CASCADE_PHYSICAL,
    EXPECTED_OLD,
    EXPECTED_OT,
    EXPECTED_RELS,
    EXPECTED_STRUCTURED,
    FORBIDDEN_MANIFEST_ENTITIES,
    PHASE2C2B_DELETE_ORDER,
    POST_MAIN,
    SOURCE_COMP,
    SOURCE_OFICIO,
    load_safe_sets_from_sources_diag,
)
from app.domains.predeploy_cleanup.phase2c2_notification_source_diag import PROTECTED_COMP_CLOSURE_8

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
SOURCES_DIAG = OUTPUT / "cleanup_phase2c2b_sources_diag_20260920.json"
MANIFEST = OUTPUT / "cleanup_execution_manifest_phase2c2b_sources_20260920.json"


@pytest.fixture
def safe_sets() -> dict:
    assert SOURCES_DIAG.is_file(), "Ejecutar diag 3G primero"
    return load_safe_sets_from_sources_diag(SOURCES_DIAG)


@pytest.fixture
def manifest() -> dict:
    assert MANIFEST.is_file(), "Ejecutar freeze_cleanup_phase2c2b_execution_manifest.py primero"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_exact_safe_counts(safe_sets: dict) -> None:
    assert len(safe_sets["actuaciones"]) == EXPECTED_ACTS
    assert len(safe_sets["relevamiento"]) == EXPECTED_RELS
    assert len(safe_sets["orden_trabajo"]) == EXPECTED_OT


def test_family_split(manifest: dict) -> None:
    fam = manifest["act_family_breakdown"]
    assert fam["SET_ACT_OLD_count"] == EXPECTED_OLD
    assert fam["SET_ACT_STRUCTURED_count"] == EXPECTED_STRUCTURED
    assert fam["BOTH_count"] == 0


def test_manifest_phase_and_entities(manifest: dict) -> None:
    assert manifest["phase"] == "2C2B"
    assert manifest["writes_executed"] is False
    assert len(manifest["entities"]["actuaciones"]) == EXPECTED_ACTS
    assert len(manifest["entities"]["relevamiento"]) == EXPECTED_RELS
    assert len(manifest["entities"]["orden_trabajo"]) == EXPECTED_OT


def test_all_ids_exist(manifest: dict) -> None:
    for entity in PHASE2C2B_DELETE_ORDER:
        assert manifest["validation"]["ids_exist"][entity]["missing"] == 0


def test_blockers_zero(manifest: dict) -> None:
    assert manifest["validation"]["act_blockers_zero"] is True
    assert manifest["validation"]["relevamiento_blockers_zero"] is True


def test_ot_exclusive(manifest: dict) -> None:
    assert manifest["validation"]["ot_exclusive"]["all_exclusive_to_safe_acts"] is True


def test_cascade_physical_counts(manifest: dict) -> None:
    for tbl, spec in EXPECTED_CASCADE_PHYSICAL.items():
        casc = manifest["expected_cascades"][tbl]
        assert casc["physical_rows"] == spec["physical_rows"]
        assert casc["expected_after"] == spec["expected_after"]


def test_actuaciones_inspector_after_4180(manifest: dict) -> None:
    ai = manifest["expected_cascades"]["actuaciones_inspector"]
    assert ai["physical_rows"] == 9
    assert ai["expected_after"] == 4180
    assert ai["expected_after"] != 4171


def test_relevamiento_relevador_after_525(manifest: dict) -> None:
    rr = manifest["expected_cascades"]["relevamiento_relevador"]
    assert rr["physical_rows"] == 10
    assert rr["expected_after"] == 525


def test_acta_inspeccion_item_zero(manifest: dict) -> None:
    assert manifest["expected_cascades"]["acta_inspeccion_item"]["physical_rows"] == 0


def test_inspeccion_physical_17(manifest: dict) -> None:
    assert manifest["expected_cascades"]["inspeccion"]["physical_rows"] == 17


def test_preserve_docs(manifest: dict) -> None:
    assert len(manifest["preserve"]["notificaciones_109"]) == 109
    assert len(manifest["preserve"]["comprobaciones_3"]) == 3
    assert manifest["preserve"]["comprobacion_2129"]["id"] == SOURCE_COMP
    assert manifest["preserve"]["oficio_1575"]["id"] == SOURCE_OFICIO
    assert SOURCE_COMP in manifest["preserve"]["comprobaciones_3"]


def test_forbidden_entities_not_in_manifest(manifest: dict) -> None:
    assert set(manifest["entities"].keys()) == set(PHASE2C2B_DELETE_ORDER)
    for forbidden in FORBIDDEN_MANIFEST_ENTITIES:
        assert forbidden not in manifest["entities"]


def test_excluded_blocked_and_orphans(manifest: dict) -> None:
    assert len(manifest["excluded"]["blocked_acts_38"]) == 38
    assert manifest["excluded"]["orphan_notificaciones_36"] == 36
    assert manifest["excluded"]["orphan_comprobaciones_20"] == 20
    assert manifest["excluded"]["relevador_qa_id_2"]["id"] == 2


def test_relevador_qa_excluded_from_entities(manifest: dict) -> None:
    assert "relevador" not in manifest["entities"]


def test_protected_closure_zero(manifest: dict) -> None:
    assert manifest["protected_intersection"] == 0
    assert manifest["protected_closure_detail"]["valid"] is True


def test_protected_comprobacion_8(manifest: dict) -> None:
    reg = manifest["protected_comprobacion_regression"]
    assert reg["all_protected"] is True
    assert set(reg["closure_8_ids"]) == set(PROTECTED_COMP_CLOSURE_8)


def test_delete_order(manifest: dict) -> None:
    assert manifest["delete_order"] == PHASE2C2B_DELETE_ORDER
    assert manifest["validation"]["delete_order_validated"]["valid"] is True


def test_post_count_arithmetic(manifest: dict) -> None:
    for entity in PHASE2C2B_DELETE_ORDER:
        before = manifest["expected_counts_before"][entity]
        after = manifest["expected_counts_after"][entity]
        n = len(manifest["entities"][entity])
        assert before - n == after
        assert after == POST_MAIN[entity]


def test_manifest_sha256_stable(manifest: dict) -> None:
    assert manifest["manifest_sha256"] == manifest_sha256(manifest)
