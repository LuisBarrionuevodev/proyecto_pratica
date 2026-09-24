"""Validaciones PREDEPLOY-CLEANUP.3M.1 — execution manifests FASE 2E catálogos."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.catalogs_phase2e_manifest_freeze import (
    BLOCKED_QA_CALLE_IDS,
    BLOCKED_TEST_JUZGADO_COUNT,
    CALLE_ALIAS_KEEP_IDS,
    EXPECTED_JUZGADO_CODIGO,
    EXPECTED_JUZGADO_NOMBRE,
    EXPECTED_RELEVADOR_NOMBRE,
    INDETERMINATE_JUZGADO_COUNT,
    JUZGADO_SAFE_ID,
    PROTECTED_JUZGADO_IDS,
    RELEVADOR_PROVENANCE,
    RELEVADOR_SAFE_ID,
    load_diag_for_freeze,
)
from app.domains.predeploy_cleanup.manifest_io import manifest_sha256

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
DIAG_3M = OUTPUT / "cleanup_catalogs_phase2e_diag_20260920.json"
MANIFEST_R = OUTPUT / "cleanup_execution_manifest_phase2e_relevador_20260920.json"
MANIFEST_J = OUTPUT / "cleanup_execution_manifest_phase2e_juzgado_20260920.json"
FREEZE_REPORT = OUTPUT / "cleanup_catalogs_phase2e_manifest_freeze_20260920.json"


@pytest.fixture
def diag_data() -> dict:
    assert DIAG_3M.is_file(), "Ejecutar diag 3M primero"
    return load_diag_for_freeze(DIAG_3M)


@pytest.fixture
def manifest_r() -> dict:
    assert MANIFEST_R.is_file(), "Ejecutar freeze 3M.1 primero"
    return json.loads(MANIFEST_R.read_text(encoding="utf-8"))


@pytest.fixture
def manifest_j() -> dict:
    assert MANIFEST_J.is_file(), "Ejecutar freeze 3M.1 primero"
    return json.loads(MANIFEST_J.read_text(encoding="utf-8"))


class TestPhase2eRelevador:
    def test_entity_set_id2(self, manifest_r: dict) -> None:
        assert manifest_r["entities"]["relevador"] == [RELEVADOR_SAFE_ID]

    def test_id2_identity_snapshot(self, manifest_r: dict) -> None:
        snap = manifest_r["identity_snapshot"][0]
        assert snap["id"] == RELEVADOR_SAFE_ID
        assert snap["nombre"] == EXPECTED_RELEVADOR_NOMBRE
        assert snap["classification"] == "CONFIRMADO_TEST_FK_FREE"
        assert set(snap["provenance"]) == set(RELEVADOR_PROVENANCE)

    def test_classification_fk_free(self, manifest_r: dict) -> None:
        assert manifest_r["classification"]["CONFIRMADO_TEST_FK_FREE"] == 1

    def test_all_fk_refs_zero(self, manifest_r: dict) -> None:
        fk = manifest_r["fk_validation"]
        assert fk["total_refs"] == 0
        assert fk["restrict_refs"] == 0
        assert fk["cascade_refs"] == 0
        assert fk["set_null_refs"] == 0
        assert fk["valid_fk_free"] is True

    def test_protected_zero(self, manifest_r: dict) -> None:
        assert manifest_r["protected_intersection"] == 0

    def test_canonical_survivors_10(self, manifest_r: dict) -> None:
        assert manifest_r["canonical_survivor_count"] == 10
        assert len(manifest_r["canonical_survivors"]) == 10

    def test_id1_preserved(self, manifest_r: dict) -> None:
        assert manifest_r["relevador_id1_preserved"]["id"] == 1
        assert manifest_r["relevador_id1_preserved"]["relevamiento_relevador_refs"] == 525
        assert RELEVADOR_SAFE_ID not in manifest_r["canonical_survivors"]

    def test_expected_11_to_10(self, manifest_r: dict) -> None:
        assert manifest_r["expected_counts_before"]["relevador"] == 11
        assert manifest_r["expected_counts_after"]["relevador"] == 10
        assert manifest_r["expected_counts_after"]["relevamiento_relevador"] == 525

    def test_expected_effects_zero_cascade(self, manifest_r: dict) -> None:
        eff = manifest_r["expected_effects"]
        assert eff["explicit_delete"] == 1
        assert eff["cascade"] == 0
        assert eff["set_null"] == 0
        assert eff["restrict"] == 0

    def test_single_entity_only(self, manifest_r: dict) -> None:
        assert list(manifest_r["entities"].keys()) == ["relevador"]
        assert manifest_r["validation"]["single_table_only"] is True

    def test_hash_stable(self, manifest_r: dict) -> None:
        assert manifest_r["manifest_sha256"] == manifest_sha256(manifest_r)

    def test_writes_not_executed(self, manifest_r: dict) -> None:
        assert manifest_r["writes_executed"] is False

    def test_phase_label(self, manifest_r: dict) -> None:
        assert manifest_r["phase"] == "2E_R_RELEVADOR"


class TestPhase2eJuzgado:
    def test_entity_set_id922(self, manifest_j: dict) -> None:
        assert manifest_j["entities"]["juzgado_catalogo"] == [JUZGADO_SAFE_ID]

    def test_id922_identity(self, manifest_j: dict) -> None:
        snap = manifest_j["identity_snapshot"][0]
        assert snap["id"] == JUZGADO_SAFE_ID
        assert snap["codigo"] == EXPECTED_JUZGADO_CODIGO
        assert snap["nombre"] == EXPECTED_JUZGADO_NOMBRE
        assert snap["classification"] == "CONFIRMADO_TEST_FK_FREE"

    def test_oficio_refs_zero(self, manifest_j: dict) -> None:
        fk = manifest_j["fk_validation"]
        assert fk["total_refs"] == 0
        assert fk["valid_fk_free"] is True

    def test_protected_zero(self, manifest_j: dict) -> None:
        assert manifest_j["protected_intersection"] == 0

    def test_protected_juzgados_excluded(self, manifest_j: dict) -> None:
        preserved = set(manifest_j["preserve"]["protected_juzgado_ids"])
        assert preserved == set(PROTECTED_JUZGADO_IDS)
        assert JUZGADO_SAFE_ID not in preserved

    def test_blocked_and_indeterminate_excluded(self, manifest_j: dict, diag_data: dict) -> None:
        assert manifest_j["preserve"]["blocked_test_juzgados_count"] == BLOCKED_TEST_JUZGADO_COUNT
        assert manifest_j["preserve"]["indeterminate_juzgados_count"] == INDETERMINATE_JUZGADO_COUNT
        delete_ids = set(manifest_j["entities"]["juzgado_catalogo"])
        blocked = set(diag_data["juzgados"]["BLOCKED_TEST_JUZGADOS"])
        indeterminate = set(diag_data["juzgados"]["INDETERMINATE_JUZGADOS"])
        assert delete_ids == {JUZGADO_SAFE_ID}
        assert delete_ids.isdisjoint(blocked)
        assert delete_ids.isdisjoint(indeterminate)

    def test_expected_843_to_842(self, manifest_j: dict) -> None:
        assert manifest_j["expected_counts_before"]["juzgado_catalogo"] == 843
        assert manifest_j["expected_counts_after"]["juzgado_catalogo"] == 842
        assert manifest_j["expected_counts_after"]["oficio"] == 1447

    def test_execution_precondition_post_r(self, manifest_j: dict) -> None:
        pre = manifest_j["execution_precondition"]
        assert pre["phase2e_r_applied"] is True
        assert pre["relevador_count"] == 10
        assert pre["phase2e_r_expected_state"]["relevador"] == 10

    def test_expected_effects_zero_cascade(self, manifest_j: dict) -> None:
        eff = manifest_j["expected_effects"]
        assert eff["explicit_delete"] == 1
        assert eff["cascade"] == 0
        assert eff["set_null"] == 0
        assert eff["restrict"] == 0

    def test_canonical_guard(self, manifest_j: dict) -> None:
        assert manifest_j["validation"]["canonical_missing_after"] == 0

    def test_single_entity_only(self, manifest_j: dict) -> None:
        assert list(manifest_j["entities"].keys()) == ["juzgado_catalogo"]

    def test_hash_stable(self, manifest_j: dict) -> None:
        assert manifest_j["manifest_sha256"] == manifest_sha256(manifest_j)

    def test_phase_label(self, manifest_j: dict) -> None:
        assert manifest_j["phase"] == "2E_J_JUZGADO"


class TestPhase2eFreezeReport:
    def test_source_diag_sha(self, diag_data: dict, manifest_r: dict) -> None:
        assert manifest_r["source_diag_sha256"]
        safe = diag_data["safe_global"]
        assert safe["SAFE_RELEVADORES_2E"] == [2]
        assert safe["SAFE_JUZGADOS_2E"] == [922]

    def test_cross_manifest_disjoint(self, manifest_r: dict, manifest_j: dict) -> None:
        assert set(manifest_r["entities"]) != set(manifest_j["entities"])
        r_ids = manifest_r["entities"]["relevador"]
        j_ids = manifest_j["entities"]["juzgado_catalogo"]
        assert r_ids != j_ids

    def test_freeze_report_exists(self) -> None:
        assert FREEZE_REPORT.is_file()
        data = json.loads(FREEZE_REPORT.read_text(encoding="utf-8"))
        assert data["writes_executed"] is False
        assert data["2e_c"]["status"] == "STOP"
        assert data["2e_c"]["blocked_qa_ids"] == list(BLOCKED_QA_CALLE_IDS)
        assert data["2e_u"]["status"] == "STOP"
        assert data["2e_c"]["alias_keep_ids"] == list(CALLE_ALIAS_KEEP_IDS)
        assert data["users_effect"]["users_affected"] == 0
        assert data["protected_guard"]["combined_protected_intersection"] == 0
