"""Validaciones PREDEPLOY-CLEANUP.3J.1 — execution manifest ROUTE-RESIDUAL."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.manifest_io import manifest_sha256
from app.domains.predeploy_cleanup.route_residual_manifest_freeze import (
    BASELINE_POST_3I2,
    EXPECTED_SAFE_ROUTES,
    POST_EXPLICIT,
    PROVENANCE_ROUTE_TO_ITEM_ACT,
    ROUTE_RESIDUAL_DELETE_ORDER,
    SAFE_RUTA_TRABAJO_RESIDUAL,
    load_safe_sets_from_diag,
)

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
DIAG_3J = OUTPUT / "cleanup_route_residual_diag_20260920.json"
MANIFEST = OUTPUT / "cleanup_execution_manifest_route_residual_20260920.json"


@pytest.fixture
def safe_sets() -> dict:
    assert DIAG_3J.is_file(), "Ejecutar diag 3J primero"
    return load_safe_sets_from_diag(DIAG_3J)


@pytest.fixture
def manifest() -> dict:
    assert MANIFEST.is_file(), "Ejecutar freeze_cleanup_route_residual_execution_manifest.py primero"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_safe_routes_count_12(safe_sets: dict) -> None:
    assert len(safe_sets["safe_ruta_trabajo"]) == EXPECTED_SAFE_ROUTES


def test_exact_route_ids(safe_sets: dict) -> None:
    assert safe_sets["safe_ruta_trabajo"] == set(SAFE_RUTA_TRABAJO_RESIDUAL)


def test_no_duplicates() -> None:
    assert len(SAFE_RUTA_TRABAJO_RESIDUAL) == len(set(SAFE_RUTA_TRABAJO_RESIDUAL))


def test_classification_confirmado_test_12(manifest: dict) -> None:
    assert manifest["classification"]["confirmado_test_route"] == EXPECTED_SAFE_ROUTES


def test_manifest_phase_and_entity(manifest: dict) -> None:
    assert manifest["phase"] == "ROUTE_RESIDUAL"
    assert manifest["writes_executed"] is False
    assert len(manifest["entities"]["ruta_trabajo"]) == EXPECTED_SAFE_ROUTES
    assert list(manifest["entities"].keys()) == ["ruta_trabajo"]


def test_all_routes_exist_no_duplicates(manifest: dict) -> None:
    ids = manifest["entities"]["ruta_trabajo"]
    assert manifest["validation"]["ids_exist"]["ruta_trabajo"]["missing"] == 0
    assert len(ids) == len(set(ids))


def test_operational_empty_revalidated(manifest: dict) -> None:
    assert manifest["validation"]["operational_empty"] is True
    for row in manifest["operational_emptiness_revalidated"]:
        assert row["ruta_item_refs"] == 0
        assert row["ruta_grupo_refs"] == 0
        assert row["ruta_grupo_inspector_refs"] == 0
        assert row["ruta_pool_dia_refs"] == 0


def test_cascade_physical_zero(manifest: dict) -> None:
    casc = manifest["expected_cascades"]
    assert casc["ruta_grupo"]["physical_rows"] == 0
    assert casc["ruta_grupo_inspector"]["physical_rows"] == 0
    assert casc["ruta_item"]["physical_rows"] == 0
    assert casc["ruta_pool_dia"]["set_null_rows"] == 0
    assert casc["other"]["physical_rows"] == 0


def test_set_null_zero(manifest: dict) -> None:
    assert manifest["expected_set_null"]["set_null_total"] == 0


def test_no_child_entities_in_delete_manifest(manifest: dict) -> None:
    assert "ruta_grupo" not in manifest["entities"]
    assert "ruta_grupo_inspector" not in manifest["entities"]
    assert "ruta_item" not in manifest["entities"]
    assert "ruta_pool_dia" not in manifest["entities"]
    assert manifest["validation"]["no_child_entities_in_manifest"] is True


def test_protected_intersection_zero(manifest: dict) -> None:
    assert manifest["protected_intersection"] == 0
    assert manifest["protected_closure_detail"]["valid"] is True


def test_known_test_guards_zero(manifest: dict) -> None:
    guards = manifest["known_test_guards"]
    assert guards["acts_remaining"] == 0
    assert guards["ot_remaining"] == 0
    assert guards["guard_ok"] is True


def test_admin_graph_preserved(manifest: dict) -> None:
    p = manifest["preserve"]
    assert len(p["admin_graph_25_notificaciones"]) == 25
    assert p["comprobacion_2289"] == 2289
    assert len(p["expedientes_27"]) == 27
    assert p["oficio_1662"] == 1662
    assert manifest["admin_graph_guard"]["touched_by_this_diag"] is False


def test_users_excluded(manifest: dict) -> None:
    assert manifest["excluded"]["users"] == "NO_DELETE"
    assert manifest["users_simulation"]["users_additionally_unlocked"] == 0


def test_postcount_ruta_trabajo(manifest: dict) -> None:
    assert manifest["expected_counts_before"]["ruta_trabajo"] == BASELINE_POST_3I2["ruta_trabajo"]
    assert manifest["expected_counts_after"]["ruta_trabajo"] == POST_EXPLICIT["ruta_trabajo"]


def test_unchanged_hard_counts(manifest: dict) -> None:
    uc = manifest["unchanged_counts"]
    assert uc["ruta_grupo"] == 2884
    assert uc["ruta_grupo_inspector"] == 5931
    assert uc["ruta_item"] == 3685
    assert uc["ruta_pool_dia"] == 361
    assert uc["iniciador_ruta"] == 8001
    assert uc["actuaciones"] == 8074
    assert uc["orden_trabajo"] == 8810
    assert uc["notificacion"] == 2478
    assert uc["comprobacion"] == 1530


def test_delete_order(manifest: dict) -> None:
    assert manifest["delete_order"] == ROUTE_RESIDUAL_DELETE_ORDER
    assert manifest["validation"]["delete_order_validated"]["valid"] is True


def test_provenance_links(manifest: dict) -> None:
    for link in manifest["provenance"]["full_links"]:
        rtid = link["ruta_trabajo_id"]
        expected = PROVENANCE_ROUTE_TO_ITEM_ACT[rtid]
        assert link["deleted_ruta_item_id"] == expected["deleted_ruta_item_id"]
        assert link["deleted_actuacion_id"] == expected["deleted_actuacion_id"]


def test_manifest_hash_stable(manifest: dict) -> None:
    stored = manifest["manifest_sha256"]
    copy = dict(manifest)
    copy.pop("manifest_sha256", None)
    assert manifest_sha256(copy) == stored
