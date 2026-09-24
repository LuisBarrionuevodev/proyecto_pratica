"""Tests PREDEPLOY-CLEANUP.2B: execution manifest y apply seguro."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.domains.predeploy_cleanup.apply_service import (
    ApplyAbortError,
    apply_phase1_cleanup,
    audit_table_engines,
    dry_run_execution_manifest,
    preflight_apply,
)
from app.domains.predeploy_cleanup.execution_manifest import (
    assert_blocked_not_in_execution,
    build_execution_manifest,
    extract_execution_ids_from_dry_run_v3,
    parse_id_set_literal,
    verify_manifest_hash,
)
from app.domains.predeploy_cleanup.manifest_io import ManifestError, manifest_sha256

BACKEND_ROOT = Path(__file__).resolve().parents[1]
EXEC_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_execution_manifest_phase1_20260920.json"
PROTECTED_PATH = BACKEND_ROOT / "scripts" / "output" / "protected_operational_manifest_20260920.json"
CLEANUP_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_manifest_phase1_20260920.json"
DRY_RUN_V3_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_phase1_dry_run_v3_20260920_015729.json"


def _minimal_execution(act_ids: list[int] = [100]) -> dict:
    return {
        "database": "digitaliza_sandbox",
        "alembic_revision": "abc",
        "execution_manifest_hash": "pending",
        "counts": {"actuaciones": len(act_ids)},
        "entities": {"actuaciones": [{"id": i} for i in act_ids]},
        "blocked_preserve": {"actuaciones": [200]},
        "precondition_snapshot": {"counts": {"actuaciones": 10}},
        "delete_order": ["actuaciones"],
    }


def test_parse_id_set_literal():
    assert parse_id_set_literal("{1, 2, 3}") == {1, 2, 3}
    assert parse_id_set_literal([4, 5]) == {4, 5}


def test_cleanup_manifest_not_accepted_for_apply_cli_guard():
    """Apply debe rechazar cleanup manifest como sustituto."""
    from scripts.cleanup_test_contamination import validate_apply_guards
    import argparse

    args = argparse.Namespace(
        apply=True,
        protected_manifest=PROTECTED_PATH,
        execution_manifest=EXEC_PATH,
        cleanup_manifest=CLEANUP_PATH,
        confirm_database="digitaliza_sandbox",
        backup_confirmed=True,
    )
    conn_db = "digitaliza_sandbox"
    with pytest.raises(SystemExit, match="no usar --cleanup-manifest"):
        validate_apply_guards(args, conn_db)


def test_execution_manifest_required_for_apply():
    from scripts.cleanup_test_contamination import validate_apply_guards
    import argparse

    args = argparse.Namespace(
        apply=True,
        protected_manifest=PROTECTED_PATH,
        execution_manifest=None,
        cleanup_manifest=None,
        confirm_database="digitaliza_sandbox",
        backup_confirmed=True,
    )
    with pytest.raises(SystemExit, match="--execution-manifest"):
        validate_apply_guards(args, "digitaliza_sandbox")


def test_blocked_id_not_in_execution_manifest():
    dry_run = json.loads(DRY_RUN_V3_PATH.read_text(encoding="utf-8"))
    cleanup = json.loads(CLEANUP_PATH.read_text(encoding="utf-8"))
    execution_ids = extract_execution_ids_from_dry_run_v3(dry_run)
    errors = assert_blocked_not_in_execution(execution_ids, dry_run, cleanup)
    assert errors == []


def test_blocked_overlap_aborts_generation():
    dry_run = {
        "dry_run_valid": True,
        "execution_validation": {"status": "EXECUTION_PLAN_VALID", "adjusted_explicit": {}},
        "executability_table": [
            {"entidad": "denuncia", "delete_final": 0, "blocked": 1},
            {"entidad": "actuaciones", "delete_final": 1, "blocked": 0},
            {"entidad": "iniciador_ruta", "delete_final": 0, "blocked": 0},
            {"entidad": "relevamiento", "delete_final": 0, "blocked": 0},
            {"entidad": "orden_trabajo", "delete_final": 0, "blocked": 0},
            {"entidad": "users", "delete_final": 0, "blocked": 0},
        ],
        "iniciador_classification": {"test_candidates_total": 0, "protected_real": [], "blocked_indeterminate": []},
        "denuncia_audit": {"blocked_ids": [99]},
        "relevamiento_audit": {"blocked_ids": []},
    }
    cleanup = {"entities": {"actuaciones": [{"id": 1}], "orden_trabajo": [], "users": []}}
    execution_ids = {
        "actuaciones": {1}, "iniciador_ruta": set(), "denuncia": {99}, "relevamiento": set(),
        "orden_trabajo": set(), "users": set(), "ruta_trabajo": set(), "ruta_item": set(),
        "ruta_pool_dia": set(), "ruta_grupo": set(), "ruta_grupo_inspector": set(),
        "juzgado_catalogo": set(), "rubro": set(), "relevador": set(),
    }
    errors = assert_blocked_not_in_execution(execution_ids, dry_run, cleanup)
    assert any("denuncia blocked" in e for e in errors)


def test_protected_intersection_aborts_build():
    conn = MagicMock()
    dry_run = json.loads(DRY_RUN_V3_PATH.read_text(encoding="utf-8"))
    protected = json.loads(PROTECTED_PATH.read_text(encoding="utf-8"))
    cleanup = json.loads(CLEANUP_PATH.read_text(encoding="utf-8"))
    execution_ids = extract_execution_ids_from_dry_run_v3(dry_run)
    prot_act = protected["entities"]["actuaciones"][0]["id"]
    dry_run["execution_validation"]["adjusted_explicit"]["actuaciones"] = str(
        execution_ids["actuaciones"] | {prot_act}
    )
    with patch(
        "app.domains.predeploy_cleanup.execution_manifest.build_precondition_snapshot",
        return_value={"database": "digitaliza_sandbox", "alembic_revision": "x", "counts": dry_run["counts_before"]},
    ):
        with pytest.raises(ManifestError, match="execution ∩ protected"):
            build_execution_manifest(
                conn, dry_run, protected, cleanup,
                source_dry_run_path=DRY_RUN_V3_PATH,
                protected_manifest_path=PROTECTED_PATH,
                cleanup_manifest_path=CLEANUP_PATH,
            )


def test_non_innodb_disables_apply():
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [("actuaciones", "MyISAM")]
    audit = audit_table_engines(conn, tables=("actuaciones",))
    assert audit["apply_enabled"] is False


def test_baseline_mismatch_aborts_preflight():
    manifest = _minimal_execution()
    manifest["execution_manifest_hash"] = manifest_sha256(manifest)
    manifest["precondition_snapshot"] = {"counts": {"actuaciones": 99999}}
    protected = {"entities": {"actuaciones": [{"id": 1}]}}
    conn = MagicMock()
    conn.execute.return_value.scalar.side_effect = lambda: 10
    with pytest.raises(ApplyAbortError, match="baseline drift"):
        preflight_apply(conn, manifest, protected, confirm_database="digitaliza_sandbox", dry_run=True)


def test_fk_blocker_aborts_preflight():
    manifest = json.loads(EXEC_PATH.read_text(encoding="utf-8"))
    protected = json.loads(PROTECTED_PATH.read_text(encoding="utf-8"))
    conn = MagicMock()
    scalars = iter(["digitaliza_sandbox", "x", 10, 10, 10, 10, 10, 10, 10, 10])
    conn.execute.return_value.scalar.side_effect = lambda: next(scalars, 10)
    conn.execute.return_value.fetchall.return_value = []
    conn.execute.return_value.fetchone.return_value = None
    with patch("app.domains.predeploy_cleanup.apply_service.audit_table_engines") as mock_eng:
        mock_eng.return_value = {"apply_enabled": True, "engines": {}, "non_transactional": {}}
        with patch("app.domains.predeploy_cleanup.apply_service.validate_execution_plan") as mock_fk:
            mock_fk.return_value = {"valid": False, "status": "BLOCKED", "blocked_ids_by_entity": {"actuaciones": [1]}}
            with pytest.raises(ApplyAbortError, match="FK blockers"):
                preflight_apply(conn, manifest, protected, confirm_database="digitaliza_sandbox", dry_run=True)


def test_apply_exception_rolls_back():
    manifest = {
        "database": "digitaliza_sandbox",
        "alembic_revision": "x",
        "execution_manifest_hash": "abc",
        "counts": {"actuaciones": 1},
        "entities": {"actuaciones": [{"id": 1}]},
        "blocked_preserve": {},
        "precondition_snapshot": {"counts": {}},
        "delete_order": ["actuaciones"],
        "source_protected_manifest_hash": "p",
    }
    protected = {"entities": {}}
    conn = MagicMock()
    trans = MagicMock()
    trans.is_active = True
    conn.begin.return_value = trans

    with patch("app.domains.predeploy_cleanup.apply_service.preflight_apply"):
        with patch("app.domains.predeploy_cleanup.apply_service._count_table", return_value=1):
            with patch("app.domains.predeploy_cleanup.apply_service._count_ids_exist", return_value=1):
                with patch("app.domains.predeploy_cleanup.apply_service._delete_explicit", side_effect=RuntimeError("boom")):
                    with pytest.raises(RuntimeError):
                        apply_phase1_cleanup(conn, manifest, protected, confirm_database="digitaliza_sandbox")
    trans.rollback.assert_called()


def test_apply_postcondition_failure_rolls_back():
    manifest = {
        "database": "digitaliza_sandbox",
        "alembic_revision": "x",
        "execution_manifest_hash": "abc",
        "counts": {"actuaciones": 1},
        "entities": {"actuaciones": [{"id": 1}]},
        "blocked_preserve": {"actuaciones": [99]},
        "precondition_snapshot": {"counts": {}},
        "delete_order": ["actuaciones"],
        "source_protected_manifest_hash": "p",
    }
    protected = {"entities": {"actuaciones": [{"id": 1}]}}
    conn = MagicMock()
    trans = MagicMock()
    trans.is_active = True
    conn.begin.return_value = trans

    with patch("app.domains.predeploy_cleanup.apply_service.preflight_apply"):
        with patch("app.domains.predeploy_cleanup.apply_service._count_table", return_value=1):
            with patch("app.domains.predeploy_cleanup.apply_service._count_ids_exist", side_effect=[1, 1, 0]):
                with patch("app.domains.predeploy_cleanup.apply_service._delete_explicit", return_value=1):
                    with pytest.raises(ApplyAbortError):
                        apply_phase1_cleanup(conn, manifest, protected, confirm_database="digitaliza_sandbox")
    trans.rollback.assert_called()


def test_execution_manifest_hash_stable():
    data = json.loads(EXEC_PATH.read_text(encoding="utf-8"))
    assert verify_manifest_hash(data)


def test_execution_ids_exact_from_v3():
    dry_run = json.loads(DRY_RUN_V3_PATH.read_text(encoding="utf-8"))
    execution = json.loads(EXEC_PATH.read_text(encoding="utf-8"))
    parsed = extract_execution_ids_from_dry_run_v3(dry_run)
    for entity, count in execution["counts"].items():
        assert len(parsed.get(entity, set())) == count


@pytest.mark.skipif(not EXEC_PATH.is_file(), reason="execution manifest no generado")
def test_frozen_execution_manifest_file_integrity():
    manifest = json.loads(EXEC_PATH.read_text(encoding="utf-8"))
    assert manifest["writes_executed"] is False
    assert manifest["planner_version"] == "v3"
    assert manifest["counts"]["actuaciones"] == 403
    assert manifest["counts"]["users"] == 1346
    assert verify_manifest_hash(manifest)
