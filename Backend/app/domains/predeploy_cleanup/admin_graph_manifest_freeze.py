"""
PREDEPLOY-CLEANUP.3K.1 — congelar execution manifests ADMIN-A + ADMIN-B.
Solo lectura. Sin DELETE/UPDATE/INSERT.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.admin_graph_diag import (
    BASELINE_POST_3J2,
    COMP_2289,
    OFICIO_1662,
    USERS_FK_FREE_POST_3J2,
    _cascade_on_delete,
    _incoming_fk_edges,
    _surviving_refs,
)
from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import (
    file_sha256,
    load_manifest,
    manifest_sha256,
    validate_ids_exist,
)
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.phase2c1_unlocked_sources_diag import _validate_delete_order_fk
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    _known_test_guard,
    _load_known_test_ids_from_manifests,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.route_residual_diag import BLOCKED_NOTIF_25, FUTURE_EXPEDIENTE_27
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _fetch_ids,
    load_user_fk_columns,
    protection_closure_check,
)

SOURCE_DIAG_SHA256 = "2046485eca336dec9b452d58a4246322949334f39a995a5e17f543fcde279e75"

ADMIN_A_NOTIF_25 = BLOCKED_NOTIF_25
ADMIN_A_EXP_25 = tuple(sorted(set(FUTURE_EXPEDIENTE_27) - {3103, 3104}))

ADMIN_B_EXP_IDS = (3103, 3104)
ADMIN_B_OFICIO = OFICIO_1662
ADMIN_B_COMP = COMP_2289
JUZGADO_922 = 922

ADMIN_A_DELETE_ORDER = ["expediente", "notificacion"]
ADMIN_B_DELETE_ORDER = ["expediente", "oficio", "comprobacion"]

EXPECTED_SIMPLE_COMPONENTS = 25
EXPECTED_CONNECTED_COMPONENTS = 26

POST_ADMIN_A = {
    "expediente_delta": -25,
    "notificacion": 2453,
}

POST_ADMIN_B_AFTER_A = {
    "expediente_delta": -2,
    "oficio_delta": -1,
    "comprobacion": 1529,
    "notificacion": 2453,
}


class ManifestFreezeError(Exception):
    """Aborta freeze manifest ADMIN-GRAPH."""


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _baseline_check_extended(conn: Connection) -> dict[str, Any]:
    """Valida baseline hard post-3J.2 + expediente/oficio actuales."""
    db = _scalar(conn, "SELECT DATABASE()")
    if db != "digitaliza_sandbox":
        raise ManifestFreezeError(f"DATABASE()={db}")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if alembic != "l7m8n9o0p1q2":
        raise ManifestFreezeError(f"alembic={alembic}")

    counts: dict[str, int] = {}
    for table, expected in BASELINE_POST_3J2.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            raise ManifestFreezeError(f"baseline {table}: {actual} != {expected}")

    expediente_count = int(_scalar(conn, "SELECT COUNT(*) FROM expediente") or 0)
    oficio_count = int(_scalar(conn, "SELECT COUNT(*) FROM oficio") or 0)
    counts["expediente"] = expediente_count
    counts["oficio"] = oficio_count

    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "baseline_ok": True,
        "drift": [],
        "expediente_baseline": expediente_count,
        "oficio_baseline": oficio_count,
    }


def load_diag_validated(diag_path: Path) -> dict[str, Any]:
    """Carga diagnóstico 3K y valida SHA + invariantes."""
    if file_sha256(diag_path) != SOURCE_DIAG_SHA256:
        raise ManifestFreezeError(f"source diag SHA mismatch: {diag_path}")
    data = json.loads(diag_path.read_text(encoding="utf-8"))
    if data.get("writes_executed") is not False:
        raise ManifestFreezeError("source diag writes_executed != false")

    cc = data.get("connected_components", {})
    if cc.get("count") != EXPECTED_CONNECTED_COMPONENTS:
        raise ManifestFreezeError(f"connected_components={cc.get('count')}")
    if cc.get("simple_notif_exp_count") != EXPECTED_SIMPLE_COMPONENTS:
        raise ManifestFreezeError(f"simple components={cc.get('simple_notif_exp_count')}")

    comp_cls = data.get("component_classification", {}).get("component_2289", {})
    if comp_cls.get("status") != "ALL_CONFIRMED_TEST_SAFE":
        raise ManifestFreezeError(f"component_2289 status={comp_cls.get('status')}")

    blocked = data.get("blocked_sets", {})
    for key in ("KEEP_ADMIN_NOTIFICACION", "KEEP_ADMIN_EXPEDIENTE", "KEEP_ADMIN_OFICIO", "KEEP_ADMIN_COMPROBACION"):
        if blocked.get(key):
            raise ManifestFreezeError(f"blocked_sets.{key} not empty")

    safe = data.get("safe_sets", {})
    if set(safe.get("SAFE_ADMIN_NOTIFICACION", [])) != set(ADMIN_A_NOTIF_25):
        raise ManifestFreezeError("SAFE_ADMIN_NOTIFICACION != frozen list")
    if set(safe.get("SAFE_ADMIN_EXPEDIENTE", [])) != set(FUTURE_EXPEDIENTE_27):
        raise ManifestFreezeError("SAFE_ADMIN_EXPEDIENTE != 27 expedientes")

    if data.get("component_classification", {}).get("safe_simple_count") != 25:
        raise ManifestFreezeError("safe_simple_count != 25")

    return data


def _validate_admin_a_mapping(conn: Connection) -> list[dict[str, Any]]:
    """Revalida mapping 1:1 notif→expediente PRORROGA_NOTIFICACION."""
    links: list[dict[str, Any]] = []
    exp_used: set[int] = set()

    for nid in ADMIN_A_NOTIF_25:
        exps = _rows(
            conn,
            """
            SELECT id, numero_expediente, anio, tipo_expediente, notificacion_id
            FROM expediente WHERE notificacion_id = :nid
            """,
            {"nid": nid},
        )
        if len(exps) != 1:
            raise ManifestFreezeError(f"notif {nid}: expediente count={len(exps)}")
        exp = exps[0]
        eid = int(exp["id"])
        if eid not in ADMIN_A_EXP_25:
            raise ManifestFreezeError(f"notif {nid}: expediente {eid} not in ADMIN_A set")
        if eid in exp_used:
            raise ManifestFreezeError(f"expediente {eid} shared by multiple notifs")
        if exp["tipo_expediente"] != "PRORROGA_NOTIFICACION":
            raise ManifestFreezeError(f"exp {eid}: tipo={exp['tipo_expediente']}")
        exp_used.add(eid)
        links.append(
            {
                "notificacion_id": nid,
                "expediente_id": eid,
                "numero_expediente": exp["numero_expediente"],
                "anio": exp["anio"],
                "tipo_expediente": exp["tipo_expediente"],
                "classification": "CONFIRMADO_TEST",
            }
        )

    if exp_used != set(ADMIN_A_EXP_25):
        missing = set(ADMIN_A_EXP_25) - exp_used
        raise ManifestFreezeError(f"unmapped expedientes: {missing}")

    return links


def _validate_expediente_no_incoming(conn: Connection, eids: set[int]) -> None:
    for eid in sorted(eids):
        refs = _surviving_refs(conn, "expediente", eid)
        if refs["total_refs"] != 0:
            raise ManifestFreezeError(f"expediente {eid} incoming refs={refs['by_fk']}")


def _validate_notif_refs_after_exp_delete(conn: Connection, nids: set[int], exp_ids: set[int]) -> None:
    """Simula delete expedientes: notifs deben quedar sin refs bloqueantes."""
    for nid in sorted(nids):
        act = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE notificacion_id = {nid}")
        ini = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE notificacion_id = {nid}")
        if act or ini:
            raise ManifestFreezeError(f"notif {nid}: act={act} ini={ini}")
        exp_refs = _rows(conn, "SELECT id FROM expediente WHERE notificacion_id = :nid", {"nid": nid})
        remaining = [r for r in exp_refs if int(r["id"]) not in exp_ids]
        if remaining:
            raise ManifestFreezeError(f"notif {nid}: expediente refs after sim={remaining}")


def _validate_cascade_zero(conn: Connection, table: str, ids: set[int]) -> dict[str, Any]:
    casc = _cascade_on_delete(conn, table, ids)
    if casc["cascade_total"] != 0 or casc["set_null_total"] != 0:
        raise ManifestFreezeError(f"{table} cascade/set_null: {casc}")
    return casc


def _protected_closure_for_entities(
    conn: Connection,
    protected_path: Path,
    entities: dict[str, set[int]],
) -> dict[str, Any]:
    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))
    virtual = VirtualDeleteState()
    for table, ids in entities.items():
        virtual.add_explicit(table, ids)
    closure = protection_closure_check(virtual, prot)
    if not closure.get("valid"):
        raise ManifestFreezeError(f"protected closure: {closure.get('conflicts', [])[:3]}")
    intersection = 0
    for table, ids in entities.items():
        intersection += len(ids & prot.get(table, set()))
    if intersection != 0:
        raise ManifestFreezeError(f"protected explicit intersection={intersection}")
    return {"valid": True, "intersection": 0, "detail": closure}


def _users_simulation(
    conn: Connection,
    deleted: dict[str, set[int]],
    label: str,
) -> dict[str, Any]:
    fk_columns = load_user_fk_columns(conn)
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    free_after = 0
    for uid in test_users:
        blocked = False
        for table, col in fk_columns:
            for r in conn.execute(text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}):
                if table in deleted and r[0] in deleted[table]:
                    continue
                blocked = True
                break
            if blocked:
                break
        if not blocked:
            free_after += 1
    return {
        "simulation": label,
        "users_test_fk_free_baseline": USERS_FK_FREE_POST_3J2,
        "users_test_fk_free_after": free_after,
        "users_additionally_unlocked": free_after - USERS_FK_FREE_POST_3J2,
        "policy": "NO_DELETE users",
    }


def _validate_admin_b_graph(conn: Connection) -> dict[str, Any]:
    """Revalida grafo comp 2289 + oficio 1662 + juzgado 922."""
    comp = conn.execute(
        text("SELECT id FROM comprobacion WHERE id = :id"),
        {"id": ADMIN_B_COMP},
    ).fetchone()
    if not comp:
        raise ManifestFreezeError("comprobacion 2289 missing")

    exp_3103 = conn.execute(
        text(
            """
            SELECT id, numero_expediente, tipo_expediente, comprobacion_id, oficio_id
            FROM expediente WHERE id = 3103
            """
        )
    ).fetchone()
    exp_3104 = conn.execute(
        text(
            """
            SELECT id, numero_expediente, tipo_expediente, comprobacion_id, oficio_id
            FROM expediente WHERE id = 3104
            """
        )
    ).fetchone()
    if not exp_3103 or not exp_3104:
        raise ManifestFreezeError("expedientes 3103/3104 missing")

    e3 = dict(exp_3103._mapping)
    e4 = dict(exp_3104._mapping)
    if e3["tipo_expediente"] != "ENVIO_ACTA" or e3["numero_expediente"] != "8430B0":
        raise ManifestFreezeError(f"exp 3103 mismatch: {e3}")
    if e3["comprobacion_id"] != ADMIN_B_COMP:
        raise ManifestFreezeError(f"exp 3103 comprobacion_id={e3['comprobacion_id']}")
    if e4["tipo_expediente"] != "RESPUESTA_OFICIO" or e4["numero_expediente"] != "8430B2":
        raise ManifestFreezeError(f"exp 3104 mismatch: {e4}")
    if e4["comprobacion_id"] != ADMIN_B_COMP or e4["oficio_id"] != ADMIN_B_OFICIO:
        raise ManifestFreezeError(f"exp 3104 refs mismatch: {e4}")

    oficio = conn.execute(
        text(
            """
            SELECT id, numero_oficio, comprobacion_id, juzgado_id
            FROM oficio WHERE id = :id
            """
        ),
        {"id": ADMIN_B_OFICIO},
    ).fetchone()
    if not oficio:
        raise ManifestFreezeError("oficio 1662 missing")
    o = dict(oficio._mapping)
    if o["numero_oficio"] != "OF8430" or o["comprobacion_id"] != ADMIN_B_COMP:
        raise ManifestFreezeError(f"oficio 1662 mismatch: {o}")
    if o["juzgado_id"] != JUZGADO_922:
        raise ManifestFreezeError(f"oficio juzgado_id={o['juzgado_id']}")

    jz = conn.execute(
        text("SELECT id, codigo, nombre FROM juzgado_catalogo WHERE id = :id"),
        {"id": JUZGADO_922},
    ).fetchone()
    if not jz:
        raise ManifestFreezeError("juzgado 922 missing")
    j = dict(jz._mapping)

    act = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE comprobacion_id = {ADMIN_B_COMP}")
    ini_c = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE comprobacion_id = {ADMIN_B_COMP}")
    ini_o = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE oficio_id = {ADMIN_B_OFICIO}")
    if act or ini_c or ini_o:
        raise ManifestFreezeError(f"surviving refs act={act} ini_c={ini_c} ini_o={ini_o}")

    _validate_expediente_no_incoming(conn, set(ADMIN_B_EXP_IDS))

    of_incoming = _surviving_refs(conn, "oficio", ADMIN_B_OFICIO)
    if of_incoming["total_refs"] != 1:
        raise ManifestFreezeError(f"oficio incoming refs={of_incoming}")
    if "expediente.oficio_id" not in of_incoming["by_fk"]:
        raise ManifestFreezeError("oficio missing expediente.oficio_id ref")

    comp_refs = _surviving_refs(conn, "comprobacion", ADMIN_B_COMP)
    if comp_refs["total_refs"] != 3:
        raise ManifestFreezeError(f"comprobacion refs before sim={comp_refs}")

    return {
        "comprobacion_id": ADMIN_B_COMP,
        "expedientes": [e3, e4],
        "oficio": o,
        "juzgado": j,
        "comprobacion_refs_before_delete": comp_refs,
        "oficio_incoming": of_incoming,
    }


def _cross_wave_disjointness() -> dict[str, Any]:
    exp_a = set(ADMIN_A_EXP_25)
    exp_b = set(ADMIN_B_EXP_IDS)
    notif_a = set(ADMIN_A_NOTIF_25)
    inter_exp = exp_a & exp_b
    if inter_exp:
        raise ManifestFreezeError(f"expediente overlap A∩B={inter_exp}")
    admin_b_all = exp_b | {ADMIN_B_OFICIO, ADMIN_B_COMP}
    if notif_a & admin_b_all:
        raise ManifestFreezeError("notif A intersects ADMIN-B entities")
    if exp_a & admin_b_all:
        raise ManifestFreezeError("exp A intersects ADMIN-B entities")
    return {
        "expediente_intersection": [],
        "notification_intersection": [],
        "fully_disjoint": True,
    }


def build_admin_a_manifest(
    conn: Connection,
    *,
    diag_path: Path,
    protected_path: Path,
    baseline: dict[str, Any],
    mapping_links: list[dict[str, Any]],
    expected_cascades: dict[str, Any],
) -> dict[str, Any]:
    exp_baseline = baseline["expediente_baseline"]
    exp_after = exp_baseline + POST_ADMIN_A["expediente_delta"]
    notif_before = BASELINE_POST_3J2["notificacion"]
    notif_after = POST_ADMIN_A["notificacion"]

    if exp_after != exp_baseline - 25:
        raise ManifestFreezeError(f"exp postcount math: {exp_baseline} -> {exp_after}")

    fk_valid = _validate_delete_order_fk(ADMIN_A_DELETE_ORDER, load_fk_edges(conn))

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "ADMIN_A",
        "phase_name": "confirmado_test_prorroga_notificacion_expediente_simple_components",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_diag_path": str(diag_path.resolve()),
        "source_diag_sha256": SOURCE_DIAG_SHA256,
        "protected_manifest_path": str(protected_path.resolve()),
        "protected_manifest_sha256": file_sha256(protected_path),
        "safe_set_counts": {
            "expediente": len(ADMIN_A_EXP_25),
            "notificacion": len(ADMIN_A_NOTIF_25),
        },
        "classification": {
            "confirmado_test_expediente": len(ADMIN_A_EXP_25),
            "confirmado_test_notificacion": len(ADMIN_A_NOTIF_25),
        },
        "entities": {
            "expediente": list(ADMIN_A_EXP_25),
            "notificacion": list(ADMIN_A_NOTIF_25),
        },
        "mapping": {
            "notification_to_expediente": mapping_links,
        },
        "delete_order": ADMIN_A_DELETE_ORDER,
        "forbidden_deletes": {
            "comprobacion": 0,
            "oficio": 0,
            "users": 0,
            "juzgado_catalogo": 0,
            "rubro": 0,
        },
        "expected_counts_before": {
            "expediente": exp_baseline,
            "notificacion": notif_before,
        },
        "expected_counts_after": {
            "expediente": exp_after,
            "notificacion": notif_after,
        },
        "unchanged_counts": {
            k: v
            for k, v in baseline["counts"].items()
            if k not in ("expediente", "notificacion")
        },
        "expected_cascades": expected_cascades,
        "expected_set_null": {
            "cascade_total": 0,
            "set_null_total": 0,
        },
        "excluded": {
            "comprobacion_2289": ADMIN_B_COMP,
            "expediente_3103": 3103,
            "expediente_3104": 3104,
            "oficio_1662": ADMIN_B_OFICIO,
            "juzgado_922": JUZGADO_922,
            "users": "NO_DELETE",
            "catalogs": "NO_DELETE",
        },
        "protected_intersection": 0,
        "fk_graph": {
            "expediente": _incoming_fk_edges(conn, "expediente"),
            "notificacion": _incoming_fk_edges(conn, "notificacion"),
        },
        "validation": {
            "mapping_1_to_1": True,
            "tipo_expediente": "PRORROGA_NOTIFICACION",
            "external_refs_zero": True,
            "delete_order_validated": fk_valid,
        },
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)
    return manifest


def build_admin_b_manifest(
    conn: Connection,
    *,
    diag_path: Path,
    protected_path: Path,
    baseline: dict[str, Any],
    graph: dict[str, Any],
    expected_cascades: dict[str, Any],
    admin_a_exp_after: int,
) -> dict[str, Any]:
    oficio_baseline = baseline["oficio_baseline"]
    exp_before_b = admin_a_exp_after
    exp_after_b = exp_before_b + POST_ADMIN_B_AFTER_A["expediente_delta"]
    oficio_after = oficio_baseline + POST_ADMIN_B_AFTER_A["oficio_delta"]
    comp_before = BASELINE_POST_3J2["comprobacion"]
    comp_after = POST_ADMIN_B_AFTER_A["comprobacion"]

    fk_valid = _validate_delete_order_fk(ADMIN_B_DELETE_ORDER, load_fk_edges(conn))

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "ADMIN_B",
        "phase_name": "confirmado_test_comprobacion_2289_oficio_chain",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_diag_path": str(diag_path.resolve()),
        "source_diag_sha256": SOURCE_DIAG_SHA256,
        "protected_manifest_path": str(protected_path.resolve()),
        "protected_manifest_sha256": file_sha256(protected_path),
        "precondition": {
            "admin_a_applied": True,
            "precondition_requires_admin_a_applied": True,
            "expected_expediente_before": exp_before_b,
            "expected_notificacion_before": POST_ADMIN_B_AFTER_A["notificacion"],
        },
        "safe_set_counts": {
            "expediente": len(ADMIN_B_EXP_IDS),
            "oficio": 1,
            "comprobacion": 1,
        },
        "classification": {
            "confirmado_test_expediente": 2,
            "confirmado_test_oficio": 1,
            "confirmado_test_comprobacion": 1,
        },
        "entities": {
            "expediente": list(ADMIN_B_EXP_IDS),
            "oficio": [ADMIN_B_OFICIO],
            "comprobacion": [ADMIN_B_COMP],
        },
        "preserve": {
            "juzgado_922": {
                "id": JUZGADO_922,
                "codigo": graph["juzgado"].get("codigo"),
                "nombre": graph["juzgado"].get("nombre"),
                "classification": "CONFIRMADO_TEST",
                "delete": False,
            },
        },
        "graph_revalidated": graph,
        "delete_order": ADMIN_B_DELETE_ORDER,
        "expected_counts_before": {
            "mode": "after_admin_a",
            "expediente": exp_before_b,
            "oficio": oficio_baseline,
            "comprobacion": comp_before,
            "notificacion": POST_ADMIN_B_AFTER_A["notificacion"],
        },
        "expected_counts_independent_before_admin_a": {
            "expediente": baseline["expediente_baseline"],
            "oficio": oficio_baseline,
            "comprobacion": comp_before,
            "notificacion": BASELINE_POST_3J2["notificacion"],
        },
        "expected_counts_after": {
            "expediente": exp_after_b,
            "oficio": oficio_after,
            "comprobacion": comp_after,
            "notificacion": POST_ADMIN_B_AFTER_A["notificacion"],
        },
        "expected_cascades": expected_cascades,
        "expected_set_null": {
            "cascade_total": 0,
            "set_null_total": 0,
        },
        "catalog_effect": {
            "juzgado_922_expected_refs_after": 0,
            "status": "READY_FOR_PHASE2E",
            "policy": "NO_DELETE juzgado in ADMIN_B",
        },
        "protected_intersection": 0,
        "fk_graph": {
            "expediente": _incoming_fk_edges(conn, "expediente"),
            "oficio": _incoming_fk_edges(conn, "oficio"),
            "comprobacion": _incoming_fk_edges(conn, "comprobacion"),
        },
        "validation": {
            "graph_exact": True,
            "external_refs_valid": True,
            "delete_order_validated": fk_valid,
        },
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)
    return manifest


def run_admin_graph_manifest_freeze(
    conn: Connection,
    *,
    diag_path: Path,
    protected_path: Path,
    manifest_paths: list[Path],
) -> dict[str, Any]:
    """Orquestador freeze manifests ADMIN-A + ADMIN-B."""
    baseline = _baseline_check_extended(conn)
    diag_data = load_diag_validated(diag_path)

    exp_baseline = baseline["expediente_baseline"]
    oficio_baseline = baseline["oficio_baseline"]

    # ADMIN-A validations
    stale_exp = validate_ids_exist(conn, "expediente", set(ADMIN_A_EXP_25), label="expediente")
    stale_notif = validate_ids_exist(conn, "notificacion", set(ADMIN_A_NOTIF_25), label="notificacion")
    if stale_exp or stale_notif:
        raise ManifestFreezeError(f"stale ADMIN-A ids exp={stale_exp} notif={stale_notif}")

    mapping_links = _validate_admin_a_mapping(conn)
    _validate_expediente_no_incoming(conn, set(ADMIN_A_EXP_25))
    _validate_notif_refs_after_exp_delete(conn, set(ADMIN_A_NOTIF_25), set(ADMIN_A_EXP_25))

    casc_a_exp = _validate_cascade_zero(conn, "expediente", set(ADMIN_A_EXP_25))
    casc_a_notif = _validate_cascade_zero(conn, "notificacion", set(ADMIN_A_NOTIF_25))
    expected_cascades_a = {
        "expediente": casc_a_exp,
        "notificacion": casc_a_notif,
        "cascade_total": 0,
        "set_null_total": 0,
    }

    closure_a = _protected_closure_for_entities(
        conn,
        protected_path,
        {"expediente": set(ADMIN_A_EXP_25), "notificacion": set(ADMIN_A_NOTIF_25)},
    )

    fk_a = _validate_delete_order_fk(ADMIN_A_DELETE_ORDER, load_fk_edges(conn))
    if not fk_a.get("valid"):
        raise ManifestFreezeError(f"ADMIN-A delete order: {fk_a.get('violations')}")

    # ADMIN-B validations
    graph_b = _validate_admin_b_graph(conn)
    stale_b = validate_ids_exist(
        conn,
        "expediente",
        set(ADMIN_B_EXP_IDS),
        label="expediente_b",
    )
    if stale_b:
        raise ManifestFreezeError(f"stale ADMIN-B expedientes: {stale_b}")
    if not _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id = :id", {"id": ADMIN_B_OFICIO}):
        raise ManifestFreezeError("oficio 1662 missing")
    if not _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": ADMIN_B_COMP}):
        raise ManifestFreezeError("comprobacion 2289 missing")

    casc_b_exp = _validate_cascade_zero(conn, "expediente", set(ADMIN_B_EXP_IDS))
    casc_b_of = _validate_cascade_zero(conn, "oficio", {ADMIN_B_OFICIO})
    casc_b_comp = _validate_cascade_zero(conn, "comprobacion", {ADMIN_B_COMP})
    expected_cascades_b = {
        "expediente": casc_b_exp,
        "oficio": casc_b_of,
        "comprobacion": casc_b_comp,
        "cascade_total": 0,
        "set_null_total": 0,
    }

    closure_b = _protected_closure_for_entities(
        conn,
        protected_path,
        {
            "expediente": set(ADMIN_B_EXP_IDS),
            "oficio": {ADMIN_B_OFICIO},
            "comprobacion": {ADMIN_B_COMP},
        },
    )

    fk_b = _validate_delete_order_fk(ADMIN_B_DELETE_ORDER, load_fk_edges(conn))
    if not fk_b.get("valid"):
        raise ManifestFreezeError(f"ADMIN-B delete order: {fk_b.get('violations')}")

    disjoint = _cross_wave_disjointness()

    known = _load_known_test_ids_from_manifests(manifest_paths)
    test_guard = _known_test_guard(conn, known)
    if not test_guard["guard_ok"]:
        raise ManifestFreezeError("known test guard failed")

    admin_a_exp_after = exp_baseline + POST_ADMIN_A["expediente_delta"]

    manifest_a = build_admin_a_manifest(
        conn,
        diag_path=diag_path,
        protected_path=protected_path,
        baseline=baseline,
        mapping_links=mapping_links,
        expected_cascades=expected_cascades_a,
    )
    manifest_a["protected_closure_detail"] = closure_a["detail"]
    manifest_a["known_test_guards"] = test_guard
    manifest_a["users_simulation"] = _users_simulation(
        conn,
        {"expediente": set(ADMIN_A_EXP_25), "notificacion": set(ADMIN_A_NOTIF_25)},
        "ADMIN-A",
    )
    manifest_a["manifest_sha256"] = manifest_sha256(manifest_a)

    manifest_b = build_admin_b_manifest(
        conn,
        diag_path=diag_path,
        protected_path=protected_path,
        baseline=baseline,
        graph=graph_b,
        expected_cascades=expected_cascades_b,
        admin_a_exp_after=admin_a_exp_after,
    )
    manifest_b["protected_closure_detail"] = closure_b["detail"]
    manifest_b["known_test_guards"] = test_guard
    manifest_b["users_simulation"] = _users_simulation(
        conn,
        {
            "expediente": set(ADMIN_A_EXP_25) | set(ADMIN_B_EXP_IDS),
            "notificacion": set(ADMIN_A_NOTIF_25),
            "oficio": {ADMIN_B_OFICIO},
            "comprobacion": {ADMIN_B_COMP},
        },
        "ADMIN-A+B",
    )
    manifest_b["manifest_sha256"] = manifest_sha256(manifest_b)

    combined_postcounts = {
        "baseline": {
            "notificacion": BASELINE_POST_3J2["notificacion"],
            "comprobacion": BASELINE_POST_3J2["comprobacion"],
            "expediente": exp_baseline,
            "oficio": oficio_baseline,
        },
        "after_admin_a": {
            "notificacion": POST_ADMIN_A["notificacion"],
            "comprobacion": BASELINE_POST_3J2["comprobacion"],
            "expediente": admin_a_exp_after,
            "oficio": oficio_baseline,
        },
        "after_admin_b": {
            "notificacion": POST_ADMIN_B_AFTER_A["notificacion"],
            "comprobacion": POST_ADMIN_B_AFTER_A["comprobacion"],
            "expediente": admin_a_exp_after + POST_ADMIN_B_AFTER_A["expediente_delta"],
            "oficio": oficio_baseline + POST_ADMIN_B_AFTER_A["oficio_delta"],
        },
    }

    return {
        "ticket": "PREDEPLOY-CLEANUP.3K.1",
        "writes_executed": False,
        "baseline": baseline,
        "source_diag_sha256": SOURCE_DIAG_SHA256,
        "admin_a": {
            "manifest": manifest_a,
            "manifest_sha256": manifest_a["manifest_sha256"],
            "counts": manifest_a["expected_counts_before"],
            "counts_after": manifest_a["expected_counts_after"],
        },
        "admin_b": {
            "manifest": manifest_b,
            "manifest_sha256": manifest_b["manifest_sha256"],
            "counts_before_after_admin_a": manifest_b["expected_counts_before"],
            "counts_after": manifest_b["expected_counts_after"],
        },
        "cross_wave_disjointness": disjoint,
        "combined_postcounts": combined_postcounts,
        "protected_guard": {
            "admin_a": closure_a,
            "admin_b": closure_b,
        },
        "known_test_guards": test_guard,
        "catalog_effect": manifest_b["catalog_effect"],
        "diag_summary": {
            "connected_components": diag_data["connected_components"]["count"],
            "safe_simple": diag_data["component_classification"]["safe_simple_count"],
            "component_2289": diag_data["component_classification"]["component_2289"]["status"],
        },
    }


def write_freeze_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
