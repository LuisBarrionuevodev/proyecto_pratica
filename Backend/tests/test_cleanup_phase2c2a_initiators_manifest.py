"""Validaciones PREDEPLOY-CLEANUP.3F.2 — execution manifest FASE 2C.2A."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.manifest_io import manifest_sha256
from app.domains.predeploy_cleanup.phase2c2a_initiators_manifest_freeze import (
    EXPECTED_RELEVAMIENTO,
    EXPECTED_RESIDUAL,
    EXPECTED_SAFE_TOTAL,
    FORBIDDEN_MANIFEST_ENTITIES,
    PHASE2C2A_DELETE_ORDER,
    POST_INICIADOR,
    PROTECTED_COMP_CLOSURE_8,
    load_safe_initiators_from_diag,
)

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
SOURCE_DIAG = OUTPUT / "cleanup_phase2c2_notification_source_diag_20260920.json"
MANIFEST = OUTPUT / "cleanup_execution_manifest_phase2c2a_initiators_20260920.json"


@pytest.fixture
def safe_data() -> dict:
    assert SOURCE_DIAG.is_file(), "Ejecutar diag 3F.1 primero"
    return load_safe_initiators_from_diag(SOURCE_DIAG)


@pytest.fixture
def manifest() -> dict:
    assert MANIFEST.is_file(), "Ejecutar freeze_cleanup_phase2c2a_execution_manifest.py primero"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_exact_safe_count(safe_data: dict) -> None:
    assert len(safe_data["all_ids"]) == EXPECTED_SAFE_TOTAL


def test_breakdown_129_26(safe_data: dict) -> None:
    assert len(safe_data["residual_ids"]) == EXPECTED_RESIDUAL
    assert len(safe_data["relevamiento_ids"]) == EXPECTED_RELEVAMIENTO


def test_manifest_phase_and_counts(manifest: dict) -> None:
    assert manifest["phase"] == "2C2A"
    assert manifest["writes_executed"] is False
    assert len(manifest["entities"]["iniciador_ruta"]) == EXPECTED_SAFE_TOTAL
    assert manifest["safe_set_counts"]["iniciador_ruta"] == EXPECTED_SAFE_TOTAL


def test_all_ids_exist(manifest: dict) -> None:
    assert manifest["validation"]["ids_exist"]["iniciador_ruta"]["missing"] == 0


def test_no_route_refs(manifest: dict) -> None:
    assert manifest["validation"]["route_refs"]["ruta_item"] == 0
    assert manifest["validation"]["route_refs"]["ruta_pool_dia"] == 0


def test_no_incoming_fk_blockers(manifest: dict) -> None:
    assert manifest["validation"]["incoming_fk_blockers"] == []


def test_excluded_indeterminate_intersection_zero(manifest: dict) -> None:
    assert manifest["validation"]["excluded_intersection"] == 0
    safe_ids = {e["id"] for e in manifest["entities"]["iniciador_ruta"]}
    excluded = set(manifest["excluded"]["blocked_initiators_indeterminate"])
    assert not (safe_ids & excluded)


def test_forbidden_entities_not_in_manifest(manifest: dict) -> None:
    assert set(manifest["entities"].keys()) == set(PHASE2C2A_DELETE_ORDER)
    for forbidden in FORBIDDEN_MANIFEST_ENTITIES:
        assert forbidden not in manifest["entities"]


def test_acts_relevamientos_not_deleted(manifest: dict) -> None:
    assert manifest["forbidden_deletes"]["actuaciones"] == 0
    assert manifest["forbidden_deletes"]["relevamiento"] == 0
    assert manifest["forbidden_deletes"]["notificacion"] == 0
    assert manifest["forbidden_deletes"]["comprobacion"] == 0


def test_protected_closure_zero(manifest: dict) -> None:
    assert manifest["protected_intersection"] == 0
    assert manifest["protected_closure_valid"] is True


def test_protected_comprobacion_8_regression(manifest: dict) -> None:
    reg = manifest["protected_comprobacion_regression"]
    assert reg["all_protected"] is True
    assert set(reg["closure_8_ids"]) == set(PROTECTED_COMP_CLOSURE_8)


def test_unlock_simulation_frozen(manifest: dict) -> None:
    assert manifest["unlock_expected"]["actuaciones"]["unlocked"] == 110
    assert manifest["unlock_expected"]["actuaciones"]["blocked"] == 38
    assert manifest["unlock_expected"]["relevamientos"]["unlocked"] == 26
    assert manifest["unlock_expected"]["relevamientos"]["blocked"] == 0


def test_post_count_arithmetic(manifest: dict) -> None:
    before = manifest["expected_counts_before"]["iniciador_ruta"]
    after = manifest["expected_counts_after"]["iniciador_ruta"]
    assert before - EXPECTED_SAFE_TOTAL == after
    assert after == POST_INICIADOR


def test_ot_future_metadata(manifest: dict) -> None:
    assert manifest["ot_exclusive_future_2c2b"]["count"] == 110


def test_delete_order(manifest: dict) -> None:
    assert manifest["delete_order"] == PHASE2C2A_DELETE_ORDER


def test_manifest_sha256_stable(manifest: dict) -> None:
    assert manifest["manifest_sha256"] == manifest_sha256(manifest)
