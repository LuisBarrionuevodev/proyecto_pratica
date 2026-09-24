"""Validaciones PREDEPLOY-CLEANUP.3K.1 — execution manifest ADMIN-B."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domains.predeploy_cleanup.admin_graph_manifest_freeze import (
    ADMIN_A_EXP_25,
    ADMIN_A_NOTIF_25,
    ADMIN_B_COMP,
    ADMIN_B_DELETE_ORDER,
    ADMIN_B_EXP_IDS,
    ADMIN_B_OFICIO,
    JUZGADO_922,
    POST_ADMIN_B_AFTER_A,
    SOURCE_DIAG_SHA256,
)
from app.domains.predeploy_cleanup.manifest_io import manifest_sha256

OUTPUT = Path(__file__).resolve().parents[1] / "scripts" / "output"
MANIFEST = OUTPUT / "cleanup_execution_manifest_admin_b_20260920.json"


@pytest.fixture
def manifest() -> dict:
    assert MANIFEST.is_file(), "Ejecutar freeze_cleanup_admin_graph_execution_manifest.py primero"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_exact_entities(manifest: dict) -> None:
    assert manifest["entities"]["expediente"] == list(ADMIN_B_EXP_IDS)
    assert manifest["entities"]["oficio"] == [ADMIN_B_OFICIO]
    assert manifest["entities"]["comprobacion"] == [ADMIN_B_COMP]


def test_graph_exact(manifest: dict) -> None:
    g = manifest["graph_revalidated"]
    e3 = next(e for e in g["expedientes"] if e["id"] == 3103)
    e4 = next(e for e in g["expedientes"] if e["id"] == 3104)
    assert e3["tipo_expediente"] == "ENVIO_ACTA"
    assert e3["numero_expediente"] == "8430B0"
    assert e3["comprobacion_id"] == ADMIN_B_COMP
    assert e4["tipo_expediente"] == "RESPUESTA_OFICIO"
    assert e4["numero_expediente"] == "8430B2"
    assert e4["oficio_id"] == ADMIN_B_OFICIO
    assert g["oficio"]["numero_oficio"] == "OF8430"
    assert g["oficio"]["juzgado_id"] == JUZGADO_922


def test_topology_exp_oficio_comp(manifest: dict) -> None:
    assert manifest["delete_order"] == ADMIN_B_DELETE_ORDER
    assert manifest["validation"]["delete_order_validated"]["valid"] is True


def test_cascade_set_null_zero(manifest: dict) -> None:
    assert manifest["expected_cascades"]["cascade_total"] == 0
    assert manifest["expected_set_null"]["set_null_total"] == 0


def test_protected_zero(manifest: dict) -> None:
    assert manifest["protected_intersection"] == 0
    assert manifest["protected_closure_detail"]["valid"] is True


def test_juzgado_preserved_not_deleted(manifest: dict) -> None:
    p = manifest["preserve"]["juzgado_922"]
    assert p["id"] == JUZGADO_922
    assert p["delete"] is False
    assert "juzgado" not in manifest["entities"]
    assert manifest["catalog_effect"]["juzgado_922_expected_refs_after"] == 0
    assert manifest["catalog_effect"]["status"] == "READY_FOR_PHASE2E"


def test_requires_admin_a_precondition(manifest: dict) -> None:
    pre = manifest["precondition"]
    assert pre["admin_a_applied"] is True
    assert pre["precondition_requires_admin_a_applied"] is True
    assert pre["expected_notificacion_before"] == POST_ADMIN_B_AFTER_A["notificacion"]


def test_postcounts_after_admin_a(manifest: dict) -> None:
    after = manifest["expected_counts_after"]
    assert after["expediente"] == manifest["expected_counts_before"]["expediente"] - 2
    assert after["comprobacion"] == POST_ADMIN_B_AFTER_A["comprobacion"]
    assert after["notificacion"] == POST_ADMIN_B_AFTER_A["notificacion"]
    assert after["oficio"] == manifest["expected_counts_before"]["oficio"] - 1


def test_disjoint_from_admin_a(manifest: dict) -> None:
    exp_a = set(ADMIN_A_EXP_25)
    assert not (set(manifest["entities"]["expediente"]) & exp_a)
    assert not (set(ADMIN_A_NOTIF_25) & set(manifest["entities"].get("notificacion", [])))


def test_users_excluded(manifest: dict) -> None:
    assert manifest["users_simulation"]["users_additionally_unlocked"] == 0


def test_manifest_hash_stable(manifest: dict) -> None:
    assert manifest["manifest_sha256"] == manifest_sha256(manifest)
    assert manifest["source_diag_sha256"] == SOURCE_DIAG_SHA256


def test_phase_and_writes(manifest: dict) -> None:
    assert manifest["phase"] == "ADMIN_B"
    assert manifest["writes_executed"] is False
