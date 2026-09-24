"""Validaciones PREDEPLOY-CLEANUP.3H.1 — execution manifest FASE 2C.2A'."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.manifest_io import manifest_sha256
from app.domains.predeploy_cleanup.phase2c2a_prime_wrappers_manifest_freeze import (
    BASELINE_POST_2C2B,
    EXPECTED_INI,
    EXPECTED_PRESERVED_SOURCE,
    EXPECTED_RI,
    EXPECTED_RN,
    EXPECTED_RO,
    EXPECTED_TEST_INITIATOR,
    FORBIDDEN_MANIFEST_ENTITIES,
    PHASE2C2A_PRIME_DELETE_ORDER,
    POST_EXPLICIT,
    load_safe_sets_from_diag,
)
from app.domains.predeploy_cleanup.phase2c2_notification_source_diag import PROTECTED_COMP_CLOSURE_8

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
SOURCE_DIAG = OUTPUT / "cleanup_phase2c2a_prime_residual_acts_diag_20260920.json"
MANIFEST = OUTPUT / "cleanup_execution_manifest_phase2c2a_prime_wrappers_20260920.json"


@pytest.fixture
def safe_data() -> dict:
    assert SOURCE_DIAG.is_file(), "Ejecutar diag 3H primero"
    return load_safe_sets_from_diag(SOURCE_DIAG)


@pytest.fixture
def manifest() -> dict:
    assert MANIFEST.is_file(), "Ejecutar freeze_cleanup_phase2c2a_prime_execution_manifest.py primero"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_exact_safe_counts(safe_data: dict) -> None:
    assert len(safe_data["ruta_item"]) == EXPECTED_RI
    assert len(safe_data["iniciador_ruta"]) == EXPECTED_INI


def test_manifest_phase_and_counts(manifest: dict) -> None:
    assert manifest["phase"] == "2C2A_PRIME"
    assert manifest["writes_executed"] is False
    assert len(manifest["entities"]["ruta_item"]) == EXPECTED_RI
    assert len(manifest["entities"]["iniciador_ruta"]) == EXPECTED_INI
    assert manifest["safe_set_counts"]["ruta_item"] == EXPECTED_RI
    assert manifest["safe_set_counts"]["iniciador_ruta"] == EXPECTED_INI


def test_classification_23_15(manifest: dict) -> None:
    cls = manifest["classification"]
    assert cls["safe_test_initiator"] == EXPECTED_TEST_INITIATOR
    assert cls["safe_wrapper_around_preserved_source"] == EXPECTED_PRESERVED_SOURCE
    preserved = [
        v
        for v in cls["by_iniciador_id"].values()
        if v["manifest_classification"] == "SAFE_WRAPPER_AROUND_PRESERVED_SOURCE"
    ]
    assert len(preserved) == EXPECTED_PRESERVED_SOURCE
    for v in preserved:
        assert v["diag_classification_original"] == "SAFE_WRAPPER_AROUND_REAL"


def test_tipo_counts_35_3(manifest: dict) -> None:
    tipo = manifest["validation"]["tipo_counts"]
    assert tipo["REINSPECCION_NOTIFICACION"] == EXPECTED_RN
    assert tipo["REINSPECCION_OFICIO"] == EXPECTED_RO


def test_all_ids_exist_no_duplicates(manifest: dict) -> None:
    for entity in PHASE2C2A_PRIME_DELETE_ORDER:
        ids = [e["id"] for e in manifest["entities"][entity]]
        assert manifest["validation"]["ids_exist"][entity]["missing"] == 0
        assert len(ids) == len(set(ids))


def test_delete_order_valid(manifest: dict) -> None:
    assert manifest["delete_order"] == PHASE2C2A_PRIME_DELETE_ORDER
    assert manifest["validation"]["delete_order_validated"]["valid"] is True


def test_ruta_item_child_blockers_zero(manifest: dict) -> None:
    assert manifest["validation"]["ruta_item_fk"]["child_blockers"] == []


def test_iniciador_blockers_after_ri_sim_zero(manifest: dict) -> None:
    assert manifest["validation"]["iniciador_fk_after_ri_sim"]["valid"] is True
    assert manifest["validation"]["iniciador_fk_after_ri_sim"]["violations"] == []


def test_source_docs_excluded(manifest: dict) -> None:
    assert "notificacion" not in manifest["entities"]
    assert "comprobacion" not in manifest["entities"]
    assert "oficio" not in manifest["entities"]
    assert "expediente" not in manifest["entities"]
    ps = manifest["preserve_sources"]
    assert len(ps["notificaciones"]) == EXPECTED_RN
    assert len(ps["oficio_chains"]) == EXPECTED_RO
    assert ps["no_direct_source_count"] == 6
    assert ps["source_119_count_referenced"] == 15
    for n in ps["notificaciones"]:
        assert n["preserve_policy"] == "NO_DELETE_NO_UPDATE"
        if n["notificacion_id"] is not None:
            assert n["source_bucket"] in ("source_119_preserved", "other_source_preserved")


def test_acts_38_excluded(manifest: dict) -> None:
    assert "actuaciones" not in manifest["entities"]
    assert len(manifest["excluded"]["actuaciones_38"]) == 38
    assert manifest["acts_38_metadata"]["SET_ACT_OLD"] == 38
    assert manifest["acts_38_metadata"]["SET_ACT_STRUCTURED"] == 0


def test_ot_38_excluded(manifest: dict) -> None:
    assert "orden_trabajo" not in manifest["entities"]
    assert len(manifest["excluded"]["orden_trabajo_38"]) == 38
    assert len(manifest["future_2c2b_prime"]["actuaciones_38"]) == 38
    assert len(manifest["future_2c2b_prime"]["orden_trabajo_38"]) == 38
    assert manifest["future_2c2b_prime"]["ot_exclusive"] is True


def test_orphan_docs_excluded(manifest: dict) -> None:
    assert len(manifest["excluded"]["orphan_notificaciones_36"]) == 36
    assert len(manifest["excluded"]["orphan_comprobaciones_20"]) == 20


def test_new_orphan_candidates_reserved(manifest: dict) -> None:
    fo = manifest["future_orphan_candidates"]
    assert len(fo["notificaciones_25"]) == 25
    assert fo["comprobacion_2289"] == [2289]
    assert "notificacion" not in manifest["entities"]
    assert "comprobacion" not in manifest["entities"]


def test_protected_closure_zero(manifest: dict) -> None:
    assert manifest["protected_intersection"] == 0
    assert manifest["protected_closure_detail"]["valid"] is True


def test_protected_comprobacion_8_regression(manifest: dict) -> None:
    reg = manifest["protected_comprobacion_regression"]
    assert reg["all_protected"] is True
    assert set(reg["closure_8_ids"]) == set(PROTECTED_COMP_CLOSURE_8)


def test_unlock_simulation_38_0(manifest: dict) -> None:
    assert manifest["unlock_expected"]["UNLOCKED_AFTER_2C2A_PRIME"] == 38
    assert manifest["unlock_expected"]["STILL_BLOCKED"] == 0
    assert len(manifest["unlock_expected"]["UNLOCKED_ids"]) == 38


def test_post_count_ruta_item(manifest: dict) -> None:
    before = manifest["expected_counts_before"]["ruta_item"]
    after = manifest["expected_counts_after"]["ruta_item"]
    assert before == BASELINE_POST_2C2B["ruta_item"]
    assert before - EXPECTED_RI == after
    assert after == POST_EXPLICIT["ruta_item"]


def test_post_count_iniciador(manifest: dict) -> None:
    before = manifest["expected_counts_before"]["iniciador_ruta"]
    after = manifest["expected_counts_after"]["iniciador_ruta"]
    assert before == BASELINE_POST_2C2B["iniciador_ruta"]
    assert before - EXPECTED_INI == after
    assert after == POST_EXPLICIT["iniciador_ruta"]


def test_other_hard_counts_unchanged(manifest: dict) -> None:
    for key, expected in BASELINE_POST_2C2B.items():
        if key in POST_EXPLICIT:
            continue
        assert manifest["unchanged_counts"][key] == expected


def test_forbidden_entities_not_in_manifest(manifest: dict) -> None:
    assert set(manifest["entities"].keys()) == set(PHASE2C2A_PRIME_DELETE_ORDER)
    for forbidden in FORBIDDEN_MANIFEST_ENTITIES:
        assert forbidden not in manifest["entities"]


def test_cascade_physical_zero(manifest: dict) -> None:
    assert manifest["expected_cascades"]["total_physical"] == 0
    assert manifest["validation"]["cascade_physical_total"] == 0


def test_source_119_preserved(manifest: dict) -> None:
    assert len(manifest["excluded"]["source_notificaciones_119"]) == 119


def test_routes_groups_not_deleted(manifest: dict) -> None:
    assert manifest["forbidden_deletes"]["ruta_trabajo"] == 0
    assert manifest["forbidden_deletes"]["ruta_grupo"] == 0
    assert manifest["forbidden_deletes"]["ruta_grupo_inspector"] == 0
    assert "groups_becoming_empty" in manifest["empty_routes_metadata"]


def test_manifest_sha256_stable(manifest: dict) -> None:
    assert manifest["manifest_sha256"] == manifest_sha256(manifest)
