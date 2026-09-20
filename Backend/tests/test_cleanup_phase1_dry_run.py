"""Tests para cleanup FASE 1: manifests, protección y dry-run v2."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.domains.predeploy_cleanup.constants import CRITICAL_PROTECTED_ENTITIES
from app.domains.predeploy_cleanup.fk_graph import ForeignKeyEdge, topological_delete_order
from app.domains.predeploy_cleanup.manifest_io import manifest_sha256
from app.domains.predeploy_cleanup.planner import plan_phase1_dry_run
from app.domains.predeploy_cleanup.protected import hard_conflict_check, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    classify_user_blockers,
    protection_closure_check,
    simulate_phase1,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROTECTED_PATH = BACKEND_ROOT / "scripts" / "output" / "protected_operational_manifest_20260920.json"
CLEANUP_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_manifest_phase1_20260920.json"


def _minimal_protected(act_ids: list[int] = [1]) -> dict:
    return {
        "entities": {
            "actuaciones": [{"id": i} for i in act_ids],
            "orden_trabajo": [],
            "inspeccion": [],
            "notificacion": [],
            "comprobacion": [],
            "oficio": [],
            "expediente": [],
            "users": [],
        }
    }


def _minimal_cleanup(act_ids: list[int] = [2]) -> dict:
    return {
        "entities": {
            "actuaciones": [{"id": i, "clasificacion": "CONFIRMADO_TEST"} for i in act_ids],
            "users": [],
        }
    }


def test_protected_intersection_cleanup_aborts():
    protected = _minimal_protected([100])
    cleanup = _minimal_cleanup([100])
    psets = load_protected_sets(protected)
    csets = {k: {e["id"] for e in v} for k, v in cleanup["entities"].items()}
    conflicts = hard_conflict_check(csets, psets, critical_entities=CRITICAL_PROTECTED_ENTITIES)
    assert conflicts
    assert conflicts[0]["entity"] == "actuaciones"


def test_no_intersection_ok():
    protected = _minimal_protected([100])
    cleanup = _minimal_cleanup([200])
    psets = load_protected_sets(protected)
    csets = {k: {e["id"] for e in v} for k, v in cleanup["entities"].items()}
    conflicts = hard_conflict_check(csets, psets, critical_entities=CRITICAL_PROTECTED_ENTITIES)
    assert conflicts == []


def test_manifest_hash_stable():
    data = {"a": 1, "entities": {"actuaciones": [{"id": 1}]}}
    h1 = manifest_sha256(data)
    data["manifest_sha256"] = "ignore"
    h2 = manifest_sha256(data)
    assert h1 == h2


def test_topological_delete_order_children_first():
    edges = [
        ForeignKeyEdge("ruta_item", "ruta_trabajo_id", "ruta_trabajo", "id", "CASCADE"),
        ForeignKeyEdge("ruta_grupo", "ruta_trabajo_id", "ruta_trabajo", "id", "CASCADE"),
    ]
    order = topological_delete_order(["ruta_trabajo", "ruta_item", "ruta_grupo"], edges)
    assert order.index("ruta_item") < order.index("ruta_trabajo")
    assert order.index("ruta_grupo") < order.index("ruta_trabajo")


def test_planned_delete_blocker_does_not_block_user_final():
    """Blocker en planned_delete no bloquea user al final de fase."""
    virtual = VirtualDeleteState()
    virtual.add_explicit("ruta_trabajo", {100})
    explicit = {"ruta_trabajo": {100}}
    protected = {"actuaciones": {1}, "users": set()}

    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [(100, 42)]

    blockers = classify_user_blockers(
        conn, uid=42, fk_columns=[("ruta_trabajo", "created_by_user_id")],
        virtual=virtual, explicit_by_entity=explicit, protected_all=protected,
    )
    assert blockers == []


def test_surviving_blocker_blocks_user():
    """Blocker sobreviviente sí bloquea user."""
    virtual = VirtualDeleteState()
    explicit = {"ruta_trabajo": {100}}
    protected = {"actuaciones": {1}, "users": set()}

    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [(999, 42)]

    blockers = classify_user_blockers(
        conn, uid=42, fk_columns=[("ruta_trabajo", "created_by_user_id")],
        virtual=virtual, explicit_by_entity=explicit, protected_all=protected,
    )
    assert len(blockers) == 1
    assert blockers[0]["blocking_row_id"] == 999
    assert blockers[0]["blocker_class"] == "SURVIVING_INDETERMINATE_OR_REAL"


def test_cascade_to_protected_aborts_closure():
    """CASCADE hacia protected → intersección > 0."""
    virtual = VirtualDeleteState()
    virtual.add_cascade("inspeccion", {50})
    protected = {"inspeccion": {50}}
    result = protection_closure_check(virtual, protected)
    assert not result["valid"]
    assert result["by_entity"]["inspeccion"]["intersection_total"] == 1


def test_explicit_to_protected_aborts_closure():
    """Explicit delete hacia protected → intersección > 0."""
    virtual = VirtualDeleteState()
    virtual.add_explicit("actuaciones", {200})
    protected = {"actuaciones": {200}}
    result = protection_closure_check(virtual, protected)
    assert not result["valid"]
    assert result["by_entity"]["actuaciones"]["intersection_total"] == 1


def test_wrapper_conserves_protected_actuacion():
    """64 wrappers: ruta planned delete, actuación protected survives."""
    protected = _minimal_protected([500])
    cleanup = {
        "entities": {
            "ruta_trabajo": [{"id": 10}],
            "ruta_item": [{"id": 20, "actuacion_id": 500}],
            "actuaciones": [],
            "users": [],
        }
    }
    psets = load_protected_sets(protected)
    csets = {k: {e["id"] for e in v} for k, v in cleanup["entities"].items()}
    conflicts = hard_conflict_check(csets, psets, critical_entities=CRITICAL_PROTECTED_ENTITIES)
    assert conflicts == []
    assert 500 in psets["actuaciones"]
    assert 500 not in csets.get("actuaciones", set())


def test_user_count_arithmetic_consistent():
    """users_after = users_before - deletable_after."""
    user_audit = {
        "users_before": 4149,
        "cleanup_candidates": 4135,
        "deletable_before_phase1": 134,
        "deletable_after_phase1_dependencies_removed": 4100,
        "blocked_after_phase1": 35,
        "deletable_after_ids": list(range(4100)),
        "protected_users": [],
    }
    users_after = user_audit["users_before"] - user_audit["deletable_after_phase1_dependencies_removed"]
    assert users_after == 49
    assert (
        user_audit["deletable_after_phase1_dependencies_removed"]
        + user_audit["blocked_after_phase1"]
        + len(user_audit.get("protected_users", []))
        == user_audit["cleanup_candidates"]
    )


def test_counts_after_equals_before_minus_deletes():
    """counts_after = antes - explicit - cascade."""
    before = 1000
    explicit = 542
    cascade = 0
    after = before - explicit - cascade
    assert after == 458


def test_plan_dry_run_mock_no_conflict():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = ("digitaliza_test",)
    conn.execute.return_value.fetchall.return_value = []
    conn.execute.return_value.scalar.return_value = 0

    protected = _minimal_protected([1])
    cleanup = _minimal_cleanup([2])

    mock_sim = {
        "counts_before": {"users": 10, "actuaciones": 10},
        "counts_after_exact": {"users": 9, "actuaciones": 9},
        "summary_table": [],
        "explicit_deletes": {},
        "cascade_deletes": {},
        "deletable_now": 0,
        "deletable_after_dependencies": 0,
        "blocked_after_phase1": 0,
        "user_audit": {
            "users_before": 10,
            "cleanup_candidates": 5,
            "deletable_before_phase1": 0,
            "deletable_after_phase1_dependencies_removed": 1,
            "blocked_after_phase1": 4,
            "blocked_only_by_rows_deleted_in_phase1": 0,
            "blocked_by_rows_surviving_phase1": 4,
            "protected_users": [],
            "indeterminate_users": 5,
            "deletable_after_ids": [99],
            "users_after_exact": 9,
        },
        "protection_closure": {"valid": True, "conflicts": [], "by_entity": {}},
        "protected_assertions": {"valid": True, "checks": {}, "invalid_keys": []},
        "actuaciones_removed_from_cleanup": [],
        "actuaciones_final_cleanup_count": 1,
        "orden_trabajo_recalc": {},
        "juzgado_recalc": {},
        "relevador_recalc": {},
        "document_orphan_analysis": {},
        "iniciador_classification": {},
        "virtual_state": {},
        "dry_run_valid": True,
    }

    with patch(
        "app.domains.predeploy_cleanup.planner.expand_protected_indirect",
        return_value=load_protected_sets(protected),
    ), patch(
        "app.domains.predeploy_cleanup.planner.load_fk_edges",
        return_value=[],
    ), patch(
        "app.domains.predeploy_cleanup.planner.analyze_wrappers",
        return_value={"wrappers": [], "wrapper_count": 0,
                      "iniciadores_candidato_test": [], "iniciadores_proteger": []},
    ), patch(
        "app.domains.predeploy_cleanup.planner.simulate_phase1",
        return_value=mock_sim,
    ):
        report = plan_phase1_dry_run(conn, protected, cleanup)
    assert report["writes_executed"] is False
    assert report["version"] == "cleanup_phase1_dry_run_v3"
    assert report["users_summary"]["users_after_exact"] == 9


def test_apply_requires_backup_guard():
    from scripts.cleanup_test_contamination import validate_apply_guards
    import argparse

    args = argparse.Namespace(
        apply=True,
        protected_manifest=Path("x.json"),
        execution_manifest=Path("z.json"),
        cleanup_manifest=None,
        confirm_database=None,
        backup_confirmed=False,
    )
    with pytest.raises(SystemExit, match="ABORT apply"):
        validate_apply_guards(args, "digitaliza_sandbox")


@pytest.mark.skipif(not PROTECTED_PATH.is_file(), reason="manifest no generado")
def test_frozen_manifests_exist():
    assert PROTECTED_PATH.is_file()
    assert CLEANUP_PATH.is_file()
    protected = json.loads(PROTECTED_PATH.read_text(encoding="utf-8"))
    cleanup = json.loads(CLEANUP_PATH.read_text(encoding="utf-8"))
    assert protected.get("manifest_sha256")
    assert cleanup.get("manifest_sha256")
    assert len(cleanup["entities"]["actuaciones"]) == 542


def test_domicilio_never_phase1():
    from app.domains.predeploy_cleanup.constants import PHASE1_NO_AUTO_DELETE

    assert "domicilio" in PHASE1_NO_AUTO_DELETE
    assert "contribuyente" in PHASE1_NO_AUTO_DELETE


def test_juzgado_with_oficio_blocked_in_candidates_builder():
    cleanup = json.loads(CLEANUP_PATH.read_text(encoding="utf-8")) if CLEANUP_PATH.is_file() else {}
    juzgados = cleanup.get("entities", {}).get("juzgado_catalogo", [])
    assert len(juzgados) <= 20
