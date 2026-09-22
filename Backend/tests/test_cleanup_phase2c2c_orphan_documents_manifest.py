"""Validaciones PREDEPLOY-CLEANUP.3I.1 — execution manifest FASE 2C.2C."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.manifest_io import manifest_sha256
from app.domains.predeploy_cleanup.phase2c2_notification_source_diag import PROTECTED_COMP_CLOSURE_8
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_manifest_freeze import (
    BASELINE_POST_3H,
    BLOCKED_COMPROBACION_2289,
    BLOCKED_NOTIFICACIONES_25,
    EMPTY_ROUTE_IDS,
    EXPECTED_BLOCKED_COMP,
    EXPECTED_BLOCKED_NOTIF,
    EXPECTED_SAFE_COMP,
    EXPECTED_SAFE_NOTIF,
    PHASE2C2C_DELETE_ORDER,
    POST_EXPLICIT,
    SAFE_COMPROBACIONES_2C2C,
    SAFE_NOTIFICACIONES_2C2C,
    load_safe_sets_from_diag,
)

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
DIAG_3I = OUTPUT / "cleanup_phase2c2c_orphan_documents_diag_20260920.json"
MANIFEST = OUTPUT / "cleanup_execution_manifest_phase2c2c_orphan_documents_20260920.json"


@pytest.fixture
def safe_sets() -> dict:
    assert DIAG_3I.is_file(), "Ejecutar diag 3I primero"
    return load_safe_sets_from_diag(DIAG_3I)


@pytest.fixture
def manifest() -> dict:
    assert MANIFEST.is_file(), "Ejecutar freeze_cleanup_phase2c2c_execution_manifest.py primero"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_exact_safe_notificaciones_count(safe_sets: dict) -> None:
    assert len(safe_sets["safe_notificacion"]) == EXPECTED_SAFE_NOTIF


def test_exact_safe_notificaciones_ids(safe_sets: dict) -> None:
    assert safe_sets["safe_notificacion"] == set(SAFE_NOTIFICACIONES_2C2C)


def test_exact_safe_comprobaciones_count(safe_sets: dict) -> None:
    assert len(safe_sets["safe_comprobacion"]) == EXPECTED_SAFE_COMP


def test_exact_safe_comprobaciones_ids(safe_sets: dict) -> None:
    assert safe_sets["safe_comprobacion"] == set(SAFE_COMPROBACIONES_2C2C)


def test_no_duplicates_in_safe_sets(safe_sets: dict) -> None:
    assert len(SAFE_NOTIFICACIONES_2C2C) == len(set(SAFE_NOTIFICACIONES_2C2C))
    assert len(SAFE_COMPROBACIONES_2C2C) == len(set(SAFE_COMPROBACIONES_2C2C))


def test_blocked_notificaciones_exact_25(safe_sets: dict) -> None:
    assert len(safe_sets["blocked_notificacion"]) == EXPECTED_BLOCKED_NOTIF
    assert safe_sets["blocked_notificacion"] == set(BLOCKED_NOTIFICACIONES_25)


def test_blocked_comprobacion_2289_excluded(safe_sets: dict) -> None:
    assert safe_sets["blocked_comprobacion"] == {BLOCKED_COMPROBACION_2289}
    assert BLOCKED_COMPROBACION_2289 not in safe_sets["safe_comprobacion"]


def test_safe_intersects_blocked_zero(safe_sets: dict) -> None:
    assert safe_sets["safe_notificacion"] & safe_sets["blocked_notificacion"] == set()
    assert safe_sets["safe_comprobacion"] & safe_sets["blocked_comprobacion"] == set()


def test_safe_notif_no_source_119_overlap(safe_sets: dict) -> None:
    assert safe_sets["safe_notificacion"] & safe_sets["source_119"] == set()


def test_manifest_phase_and_entities(manifest: dict) -> None:
    assert manifest["phase"] == "2C2C"
    assert manifest["writes_executed"] is False
    assert len(manifest["entities"]["notificacion"]) == EXPECTED_SAFE_NOTIF
    assert len(manifest["entities"]["comprobacion"]) == EXPECTED_SAFE_COMP


def test_all_safe_ids_exist_no_duplicates(manifest: dict) -> None:
    for entity in PHASE2C2C_DELETE_ORDER:
        ids = manifest["entities"][entity]
        assert manifest["validation"]["ids_exist"][entity]["missing"] == 0
        assert len(ids) == len(set(ids))


def test_safe_fk_zero(manifest: dict) -> None:
    assert manifest["validation"]["safe_fk_zero"]["notificacion"]["all_zero"] is True
    assert manifest["validation"]["safe_fk_zero"]["comprobacion"]["all_zero"] is True


def test_cascade_and_set_null_zero(manifest: dict) -> None:
    assert manifest["validation"]["cascade_physical_total"] == 0
    assert manifest["validation"]["set_null_physical_total"] == 0
    assert manifest["expected_cascades"]["cascade_total"] == 0
    assert manifest["expected_set_null"]["set_null_total"] == 0
    assert manifest["validation"]["notificacion_motivo_physical_rows"] == 0


def test_blocked_notificaciones_have_expediente_refs(manifest: dict) -> None:
    links = manifest["blocked_notificacion_expediente_links"]
    assert len(links) == EXPECTED_BLOCKED_NOTIF
    for link in links:
        assert link["expediente_count"] >= 1


def test_comprobacion_2289_admin_chain(manifest: dict) -> None:
    audit = manifest["comprobacion_2289_audit"]
    assert audit["comprobacion_id"] == BLOCKED_COMPROBACION_2289
    assert audit["keep_policy"] == "KEEP_ADMIN_CHAIN"
    assert audit["expediente_comprobacion_count"] == 2
    assert audit["oficio_comprobacion_count"] == 1
    assert any(o["id"] == 1662 for o in audit["oficios"])
    assert any(e["id"] == 3104 for e in audit["expedientes_via_oficio"])


def test_comprobacion_2289_not_in_entities(manifest: dict) -> None:
    assert BLOCKED_COMPROBACION_2289 not in manifest["entities"]["comprobacion"]


def test_blocked_notificaciones_not_in_entities(manifest: dict) -> None:
    entity_notif = set(manifest["entities"]["notificacion"])
    for nid in BLOCKED_NOTIFICACIONES_25:
        assert nid not in entity_notif


def test_protected_intersection_zero(manifest: dict) -> None:
    assert manifest["protected_intersection"] == 0
    assert manifest["protected_closure_detail"]["valid"] is True


def test_safe_notif_not_in_protected_closure(manifest: dict) -> None:
    safe_comp = set(manifest["entities"]["comprobacion"])
    assert safe_comp & PROTECTED_COMP_CLOSURE_8 == set()


def test_known_test_guards_zero(manifest: dict) -> None:
    guards = manifest["known_test_guards"]
    assert guards["acts_remaining"] == 0
    assert guards["ot_remaining"] == 0
    assert guards["guard_ok"] is True


def test_empty_routes_excluded(manifest: dict) -> None:
    assert len(manifest["empty_routes_residual"]) == 12
    assert manifest["preserve"]["empty_routes_12"] == list(EMPTY_ROUTE_IDS)
    for r in manifest["empty_routes_residual"]:
        assert r["ruta_item_refs"] == 0


def test_postcounts(manifest: dict) -> None:
    assert manifest["expected_counts_before"]["notificacion"] == BASELINE_POST_3H["notificacion"]
    assert manifest["expected_counts_after"]["notificacion"] == POST_EXPLICIT["notificacion"]
    assert manifest["expected_counts_after"]["comprobacion"] == POST_EXPLICIT["comprobacion"]
    assert manifest["unchanged_counts"]["actuaciones"] == 8074
    assert manifest["unchanged_counts"]["orden_trabajo"] == 8810


def test_delete_order_valid(manifest: dict) -> None:
    assert manifest["delete_order"] == PHASE2C2C_DELETE_ORDER
    assert manifest["validation"]["delete_order_validated"]["valid"] is True


def test_users_simulation(manifest: dict) -> None:
    sim = manifest["users_unlock_simulation"]
    assert sim["users_test_fk_free_after_2c2c_sim"] == 833
    assert sim["users_additionally_unlocked"] == 0


def test_source_119_safe_overlap_zero(manifest: dict) -> None:
    assert manifest["source_119_cross"]["count_safe_overlap"] == 0
    assert manifest["source_119_cross"]["safe_cap_source_119"] == []


def test_future_admin_not_safe_delete(manifest: dict) -> None:
    fa = manifest["future_admin_graph"]
    assert "FUTURE_ADMIN_GRAPH_CANDIDATE" in fa["policy"]
    assert len(fa["notification_expediente_ids"]) == EXPECTED_BLOCKED_NOTIF


def test_manifest_hash_stable(manifest: dict) -> None:
    stored = manifest["manifest_sha256"]
    copy = dict(manifest)
    copy.pop("manifest_sha256", None)
    assert manifest_sha256(copy) == stored


def test_forbidden_entities_not_in_manifest(manifest: dict) -> None:
    assert "actuaciones" not in manifest["entities"]
    assert "iniciador_ruta" not in manifest["entities"]
    assert "expediente" not in manifest["entities"]
