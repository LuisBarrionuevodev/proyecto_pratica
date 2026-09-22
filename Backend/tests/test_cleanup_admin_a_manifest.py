"""Validaciones PREDEPLOY-CLEANUP.3K.1 — execution manifest ADMIN-A."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.admin_graph_manifest_freeze import (
    ADMIN_A_DELETE_ORDER,
    ADMIN_A_EXP_25,
    ADMIN_A_NOTIF_25,
    ADMIN_B_COMP,
    ADMIN_B_EXP_IDS,
    ADMIN_B_OFICIO,
    JUZGADO_922,
    POST_ADMIN_A,
    SOURCE_DIAG_SHA256,
    load_diag_validated,
)
from app.domains.predeploy_cleanup.manifest_io import manifest_sha256

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
DIAG_3K = OUTPUT / "cleanup_admin_graph_diag_20260920.json"
MANIFEST = OUTPUT / "cleanup_execution_manifest_admin_a_20260920.json"


@pytest.fixture
def diag() -> dict:
    assert DIAG_3K.is_file(), "Ejecutar diag 3K primero"
    return load_diag_validated(DIAG_3K)


@pytest.fixture
def manifest() -> dict:
    assert MANIFEST.is_file(), "Ejecutar freeze_cleanup_admin_graph_execution_manifest.py primero"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_source_diag_sha(diag: dict) -> None:
    assert diag["writes_executed"] is False


def test_exact_25_expedientes(manifest: dict) -> None:
    assert len(manifest["entities"]["expediente"]) == 25
    assert set(manifest["entities"]["expediente"]) == set(ADMIN_A_EXP_25)


def test_exact_25_notificaciones(manifest: dict) -> None:
    assert len(manifest["entities"]["notificacion"]) == 25
    assert set(manifest["entities"]["notificacion"]) == set(ADMIN_A_NOTIF_25)


def test_no_duplicates() -> None:
    assert len(ADMIN_A_EXP_25) == len(set(ADMIN_A_EXP_25))
    assert len(ADMIN_A_NOTIF_25) == len(set(ADMIN_A_NOTIF_25))


def test_mapping_1_to_1(manifest: dict) -> None:
    links = manifest["mapping"]["notification_to_expediente"]
    assert len(links) == 25
    notifs = {l["notificacion_id"] for l in links}
    exps = {l["expediente_id"] for l in links}
    assert notifs == set(ADMIN_A_NOTIF_25)
    assert exps == set(ADMIN_A_EXP_25)
    for link in links:
        assert link["tipo_expediente"] == "PRORROGA_NOTIFICACION"


def test_topology_exp_then_notif(manifest: dict) -> None:
    assert manifest["delete_order"] == ADMIN_A_DELETE_ORDER
    assert manifest["validation"]["delete_order_validated"]["valid"] is True


def test_cascade_zero(manifest: dict) -> None:
    assert manifest["expected_cascades"]["cascade_total"] == 0
    assert manifest["expected_set_null"]["set_null_total"] == 0


def test_protected_intersection_zero(manifest: dict) -> None:
    assert manifest["protected_intersection"] == 0
    assert manifest["protected_closure_detail"]["valid"] is True


def test_postcounts(manifest: dict) -> None:
    assert manifest["expected_counts_after"]["notificacion"] == POST_ADMIN_A["notificacion"]
    before = manifest["expected_counts_before"]["expediente"]
    after = manifest["expected_counts_after"]["expediente"]
    assert after == before - 25


def test_admin_b_entities_excluded(manifest: dict) -> None:
    ex = set(manifest["entities"]["expediente"])
    assert not (set(ADMIN_B_EXP_IDS) & ex)
    assert manifest["excluded"]["comprobacion_2289"] == ADMIN_B_COMP
    assert manifest["excluded"]["oficio_1662"] == ADMIN_B_OFICIO
    assert manifest["excluded"]["juzgado_922"] == JUZGADO_922


def test_users_excluded(manifest: dict) -> None:
    assert manifest["excluded"]["users"] == "NO_DELETE"
    assert manifest["users_simulation"]["users_additionally_unlocked"] == 0


def test_manifest_hash_stable(manifest: dict) -> None:
    assert manifest["manifest_sha256"] == manifest_sha256(manifest)
    assert manifest["source_diag_sha256"] == SOURCE_DIAG_SHA256


def test_phase_and_writes(manifest: dict) -> None:
    assert manifest["phase"] == "ADMIN_A"
    assert manifest["writes_executed"] is False
