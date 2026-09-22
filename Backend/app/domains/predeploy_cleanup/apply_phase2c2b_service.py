"""Aplicación FASE 2C.2B: DELETE 110 actuaciones + 26 relevamientos + 110 OT."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.apply_service import (
    ApplyAbortError,
    _assert_admin_and_fabian,
    audit_table_engines,
    check_fk_orphans,
)
from app.domains.predeploy_cleanup.constants import RELEVAMIENTOS_QA_IDS, SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import entity_ids, manifest_sha256, validate_ids_exist
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar, audit_otro_relevador_qa
from app.domains.predeploy_cleanup.phase2c1_unlocked_sources_diag import _validate_delete_order_fk
from app.domains.predeploy_cleanup.phase2c2b_cascade_reconcile import (
    _reconcile_acta_inspeccion_item,
    _reconcile_actuaciones_inspector,
    _reconcile_inspeccion,
    _reconcile_relevamiento_relevador,
    _reconcile_simple_child,
)
from app.domains.predeploy_cleanup.phase2c2b_sources_manifest_freeze import (
    EXPECTED_ACTS,
    EXPECTED_CASCADE_PHYSICAL,
    EXPECTED_OT,
    EXPECTED_RELS,
    PHASE2C2B_DELETE_ORDER,
    POST_MAIN,
    SOURCE_COMP,
    SOURCE_OFICIO,
    SOURCE_9110_ACT,
    _baseline_check,
    _protected_closure,
    _protected_comp_regression,
    _validate_act_blockers,
    _validate_ot_exclusive,
    _validate_parent_docs,
    _validate_rel_blockers,
    load_cascade_reconcile,
    load_safe_sets_from_sources_diag,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    _chunk_ids,
    _fetch_ids,
    _table_for_entity,
    load_user_fk_columns,
)

EXPECTED_EXEC_HASH = "da12bff4604d140d795055e2e152940f4a5ffd74622d80c032455417089b52d9"
EXPECTED_SOURCE_DIAG_HASH = "3295b6229ca458b51ddbe789c215aefff6da1beecd2d0d1a4dc6988a210bb622"
EXPECTED_CASCADE_RECONCILE_HASH = "9e46a0f20faedba5cd79610b6c3fffc258f41b580cdabb1d095ea1e5e898f1b5"
EXPECTED_PROT_HASH = "d8a1fda3a10e46dcdb90b22038d73e1e08c76754a59c96dc11cff4377a3b102e"

CHILD_TABLES = (
    "inspeccion",
    "actuaciones_inspector",
    "acta_inspeccion_item",
    "clausura",
    "decomiso",
    "relevamiento_relevador",
)

UNCHANGED_TABLES = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "denuncia": 417,
    "ruta_trabajo": 2715,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3697,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8039,
}

PROTECTED_POSTCONDITION_MIN = {
    "actuaciones": 1189,
    "orden_trabajo": 1176,
    "inspeccion": 170,
    "notificacion": 168,
    "comprobacion": 56,
    "oficio": 40,
    "expediente": 40,
}

ORPHAN_TABLES = (
    "actuaciones",
    "inspeccion",
    "actuaciones_inspector",
    "acta_inspeccion_item",
    "relevamiento",
    "relevamiento_relevador",
    "orden_trabajo",
    "notificacion",
    "comprobacion",
    "oficio",
    "expediente",
    "iniciador_ruta",
)

FK_CASCADE_PAIRS = (
    ("actuaciones", "inspeccion", "actuacion_id"),
    ("actuaciones", "actuaciones_inspector", "actuaciones_id"),
    ("inspeccion", "acta_inspeccion_item", "acta_inspeccion_id"),
    ("relevamiento", "relevamiento_relevador", "relevamiento_id"),
)


def _count(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _count_ids_exist(conn: Connection, table: str, ids: set[int]) -> int:
    if not ids:
        return 0
    found = 0
    for chunk in _chunk_ids(ids, 400):
        ph = ",".join(str(i) for i in chunk)
        found += int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE id IN ({ph})") or 0)
    return found


def _delete_ids(conn: Connection, table: str, ids: set[int]) -> int:
    deleted = 0
    for chunk in _chunk_ids(ids, 400):
        ph = ",".join(str(i) for i in chunk)
        result = conn.execute(text(f"DELETE FROM `{table}` WHERE id IN ({ph})"))
        deleted += result.rowcount or 0
    return deleted


def _load_entity_sets(execution_manifest: dict[str, Any]) -> dict[str, set[int]]:
    sets: dict[str, set[int]] = {}
    expected = {"actuaciones": EXPECTED_ACTS, "relevamiento": EXPECTED_RELS, "orden_trabajo": EXPECTED_OT}
    for entity in PHASE2C2B_DELETE_ORDER:
        ids = entity_ids(execution_manifest, entity)
        if len(ids) != expected[entity]:
            raise ApplyAbortError(f"{entity} count {len(ids)} != {expected[entity]}")
        sets[entity] = ids
    return sets


def _load_preserved_from_manifest(execution_manifest: dict[str, Any]) -> dict[str, Any]:
    preserve = execution_manifest.get("preserve", {})
    notifs = {int(x) for x in preserve.get("notificaciones_109", [])}
    comps = {int(x) for x in preserve.get("comprobaciones_3", [])}
    source_notifs = {int(x) for x in preserve.get("source_notificaciones_119", [])}
    if len(notifs) != 109 or len(comps) != 3:
        raise ApplyAbortError("parent doc preserve count mismatch")
    return {
        "notificacion": notifs,
        "comprobacion": comps,
        "source_notificaciones_119": source_notifs,
        "comprobacion_2129": SOURCE_COMP,
        "oficio_1575": SOURCE_OFICIO,
    }


def _load_orphan_ids(
    notif_source_diag_path: Path | None,
    residual_graph_diag_path: Path | None,
) -> dict[str, set[int]]:
    orphan_notifs: set[int] = set()
    orphan_comps: set[int] = set()
    if notif_source_diag_path and notif_source_diag_path.is_file():
        nd = json.loads(notif_source_diag_path.read_text(encoding="utf-8"))
        orphan_notifs = {
            int(x)
            for x in (
                nd.get("notifications_199_frozen", {}).get("ORPHAN_CONFIRMED_TEST", [])
                or nd.get("orphan_docs_reserved", {}).get("notificaciones_36_ORPHAN_CONFIRMED_TEST", [])
            )
        }
    if residual_graph_diag_path and residual_graph_diag_path.is_file():
        rd = json.loads(residual_graph_diag_path.read_text(encoding="utf-8"))
        orphan_comps = {
            int(x)
            for x in rd.get("safe_sets", {}).get("SAFE_COMPROBACION_ORPHAN_TEST", [])
        }
    return {"notificacion": orphan_notifs, "comprobacion": orphan_comps}


def _validate_fk_cascade_rules(conn: Connection) -> dict[str, str]:
    edges = load_fk_edges(conn)
    rules: dict[str, str] = {}
    for parent, child, col in FK_CASCADE_PAIRS:
        rule = next(
            (e.delete_rule for e in edges if e.child_table == child and e.child_column == col),
            None,
        )
        if rule != "CASCADE":
            raise ApplyAbortError(f"FK {parent}->{child}.{col} DELETE_RULE={rule}, expected CASCADE")
        rules[f"{parent}->{child}"] = rule
    return rules


def _recalc_cascade_physical(conn: Connection, act_ids: set[int], rel_ids: set[int]) -> dict[str, int]:
    insp = _reconcile_inspeccion(conn, act_ids)
    ai = _reconcile_actuaciones_inspector(conn, act_ids)
    aii = _reconcile_acta_inspeccion_item(conn, set(insp["inspeccion_ids"]))
    claus = _reconcile_simple_child(conn, "clausura", "actuacion_id", act_ids)
    deco = _reconcile_simple_child(conn, "decomiso", "actuacion_id", act_ids)
    rr = _reconcile_relevamiento_relevador(conn, rel_ids)
    return {
        "inspeccion": insp["physical_rows"],
        "actuaciones_inspector": ai["physical_rows"],
        "acta_inspeccion_item": aii["physical_rows"],
        "clausura": claus["physical_rows"],
        "decomiso": deco["physical_rows"],
        "relevamiento_relevador": rr["physical_rows"],
    }


def _verify_preserved_docs(conn: Connection, preserved: dict[str, Any]) -> None:
    for nid in preserved["notificacion"]:
        if not _scalar(conn, "SELECT COUNT(*) FROM notificacion WHERE id = :id", {"id": nid}):
            raise ApplyAbortError(f"notificacion {nid} missing")
    for cid in preserved["comprobacion"]:
        if not _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": cid}):
            raise ApplyAbortError(f"comprobacion {cid} missing")
    if not _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": SOURCE_COMP}):
        raise ApplyAbortError("comprobacion 2129 missing")
    if not _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id = :id", {"id": SOURCE_OFICIO}):
        raise ApplyAbortError("oficio 1575 missing")


def preflight_phase2c2b_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    sources_diag_path: Path,
    cascade_reconcile_path: Path,
    *,
    notif_source_diag_path: Path | None = None,
    residual_graph_diag_path: Path | None = None,
    confirm_database: str,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_cascade_hash: str,
    expected_prot_hash: str,
    backup_confirmed: bool = False,
) -> dict[str, Any]:
    """Preflight FASE 2C.2B antes de BEGIN."""
    errors: list[str] = []

    if not backup_confirmed:
        errors.append("backup_confirmed required")

    manifest_for_hash = {k: v for k, v in execution_manifest.items() if not k.startswith("_")}
    computed = manifest_sha256(manifest_for_hash)
    if computed != expected_exec_hash:
        errors.append(f"execution hash {computed} != {expected_exec_hash}")
    if execution_manifest.get("source_diag_sha256") != expected_source_diag_hash:
        errors.append("source_diag_sha256 mismatch")
    if execution_manifest.get("cascade_reconcile_sha256") != expected_cascade_hash:
        errors.append("cascade_reconcile_sha256 mismatch")
    if execution_manifest.get("protected_manifest_sha256") != expected_prot_hash:
        errors.append("protected_manifest_sha256 mismatch")

    baseline: dict[str, Any] = {}
    entity_sets: dict[str, set[int]] = {}
    cascade_physical: dict[str, int] = {}
    try:
        baseline = _baseline_check(conn)
        loaded = load_safe_sets_from_sources_diag(sources_diag_path)
        diag = loaded["diag"]
        entity_sets = _load_entity_sets(execution_manifest)
        if entity_sets["actuaciones"] != loaded["actuaciones"]:
            errors.append("manifest acts != sources diag")
        if entity_sets["relevamiento"] != loaded["relevamiento"]:
            errors.append("manifest rels != sources diag")
        if entity_sets["orden_trabajo"] != loaded["orden_trabajo"]:
            errors.append("manifest ots != sources diag")

        fam = execution_manifest.get("act_family_breakdown", {})
        if fam.get("SET_ACT_OLD_count") != 101 or fam.get("SET_ACT_STRUCTURED_count") != 9:
            errors.append("family breakdown mismatch")

        prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
        reconcile = load_cascade_reconcile(cascade_reconcile_path)

        for entity in PHASE2C2B_DELETE_ORDER:
            stale = validate_ids_exist(conn, entity, entity_sets[entity], label=entity)
            if stale:
                errors.append(f"missing {entity}: {stale[:3]}")

        _validate_act_blockers(conn, entity_sets["actuaciones"])
        _validate_rel_blockers(conn, entity_sets["relevamiento"])
        for rid in RELEVAMIENTOS_QA_IDS:
            if rid not in entity_sets["relevamiento"]:
                errors.append(f"QA relev {rid} missing")

        if entity_sets["actuaciones"] & prot.get("actuaciones", set()):
            errors.append("protected act intersection")

        _validate_ot_exclusive(
            conn, entity_sets["orden_trabajo"], entity_sets["actuaciones"], prot
        )
        _validate_parent_docs(conn, diag, entity_sets["actuaciones"])
        comp_reg = _protected_comp_regression(conn, prot)
        if not comp_reg["all_protected"]:
            errors.append("protected comprobacion regression")

        blocked = set(execution_manifest.get("excluded", {}).get("blocked_acts_38", []))
        if len(blocked) != 38 or entity_sets["actuaciones"] & blocked:
            errors.append("blocked acts invalid")
        if _count_ids_exist(conn, "actuaciones", blocked) != 38:
            errors.append("blocked acts not all present")

        cascade_physical = _recalc_cascade_physical(
            conn, entity_sets["actuaciones"], entity_sets["relevamiento"]
        )
        for tbl, spec in EXPECTED_CASCADE_PHYSICAL.items():
            if cascade_physical.get(tbl, -1) != spec["physical_rows"]:
                errors.append(f"cascade {tbl}: {cascade_physical.get(tbl)} != {spec['physical_rows']}")

        fk_rules = _validate_fk_cascade_rules(conn)
        closure = _protected_closure(entity_sets, reconcile, prot)
        if not closure.get("valid"):
            errors.append("protected closure failed")

        preserved = _load_preserved_from_manifest(execution_manifest)
        _verify_preserved_docs(conn, preserved)

        orphan_ids = _load_orphan_ids(notif_source_diag_path, residual_graph_diag_path)
        if len(orphan_ids["notificacion"]) != 36:
            errors.append(f"orphan notif ids: {len(orphan_ids['notificacion'])}")
        if len(orphan_ids["comprobacion"]) != 20:
            errors.append(f"orphan comp ids: {len(orphan_ids['comprobacion'])}")
        if _count_ids_exist(conn, "notificacion", orphan_ids["notificacion"]) != 36:
            errors.append("orphan notifs not all present")
        if _count_ids_exist(conn, "comprobacion", orphan_ids["comprobacion"]) != 20:
            errors.append("orphan comps not all present")

        source_ids = preserved["source_notificaciones_119"]
        if _count_ids_exist(conn, "notificacion", source_ids) != len(source_ids):
            errors.append("source notificaciones missing")

        fk_valid = _validate_delete_order_fk(PHASE2C2B_DELETE_ORDER, load_fk_edges(conn))
        if not fk_valid.get("valid"):
            errors.append(f"delete order: {fk_valid.get('violations')}")

    except Exception as exc:
        errors.append(str(exc))

    engine_audit = audit_table_engines(conn, tuple(PHASE2C2B_DELETE_ORDER))
    if not engine_audit["apply_enabled"]:
        errors.append(f"non-InnoDB: {engine_audit['non_transactional']}")

    try:
        _assert_admin_and_fabian(conn)
    except ApplyAbortError as exc:
        errors.append(str(exc))

    if errors:
        raise ApplyAbortError("; ".join(errors))

    return {
        "status": "PREFLIGHT_OK",
        "baseline": baseline,
        "cascade_physical": cascade_physical,
        "fk_cascade_rules": fk_rules,
        "protected_closure": closure,
        "protected_comprobacion_regression": comp_reg,
    }


def apply_phase2c2b_sources_cleanup(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    sources_diag_path: Path,
    cascade_reconcile_path: Path,
    *,
    notif_source_diag_path: Path | None = None,
    residual_graph_diag_path: Path | None = None,
    confirm_database: str,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_cascade_hash: str,
    expected_prot_hash: str,
    backup_path: str,
    backup_hash: str,
    backup_size: int,
    restore_verified: bool,
    freeze_method: str,
) -> dict[str, Any]:
    """Aplica DELETE FASE 2C.2B en transacción única."""
    entity_sets = _load_entity_sets(execution_manifest)
    preserved = _load_preserved_from_manifest(execution_manifest)
    blocked_38 = set(execution_manifest.get("excluded", {}).get("blocked_acts_38", []))
    orphan_ids = _load_orphan_ids(notif_source_diag_path, residual_graph_diag_path)
    source_notif_ids = preserved["source_notificaciones_119"]

    counts_before = {t: _count(conn, t) for t in list(POST_MAIN) + list(CHILD_TABLES)}
    for t, v in UNCHANGED_TABLES.items():
        counts_before[t] = v

    preflight = preflight_phase2c2b_apply(
        conn,
        execution_manifest,
        protected_manifest,
        sources_diag_path,
        cascade_reconcile_path,
        notif_source_diag_path=notif_source_diag_path,
        residual_graph_diag_path=residual_graph_diag_path,
        confirm_database=confirm_database,
        expected_exec_hash=expected_exec_hash,
        expected_source_diag_hash=expected_source_diag_hash,
        expected_cascade_hash=expected_cascade_hash,
        expected_prot_hash=expected_prot_hash,
        backup_confirmed=True,
    )

    if not restore_verified:
        raise ApplyAbortError("restore_verified required")

    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    expected_cascades = _recalc_cascade_physical(
        conn, entity_sets["actuaciones"], entity_sets["relevamiento"]
    )
    child_post = {tbl: spec["expected_after"] for tbl, spec in EXPECTED_CASCADE_PHYSICAL.items()}

    if conn.in_transaction():
        conn.rollback()

    explicit_deleted: dict[str, int] = {}
    cascade_deleted: dict[str, int] = {}
    trans = conn.begin()
    try:
        child_counts_before = {t: _count(conn, t) for t in CHILD_TABLES if t != "relevamiento_relevador"}
        rr_before = _count(conn, "relevamiento_relevador")

        explicit_deleted["actuaciones"] = _delete_ids(conn, "actuaciones", entity_sets["actuaciones"])
        if explicit_deleted["actuaciones"] != EXPECTED_ACTS:
            raise ApplyAbortError(f"act deleted {explicit_deleted['actuaciones']} != {EXPECTED_ACTS}")
        if _count_ids_exist(conn, "actuaciones", entity_sets["actuaciones"]):
            raise ApplyAbortError("act ids remain")

        for tbl in ("inspeccion", "actuaciones_inspector", "clausura", "decomiso"):
            after = _count(conn, tbl)
            deleted_n = child_counts_before[tbl] - after
            expected = expected_cascades[tbl]
            if deleted_n != expected:
                raise ApplyAbortError(f"cascade {tbl}: deleted {deleted_n} != {expected}")
            if after != child_post[tbl]:
                raise ApplyAbortError(f"cascade post {tbl}: {after} != {child_post[tbl]}")
            cascade_deleted[tbl] = deleted_n

        if _count(conn, "acta_inspeccion_item") != child_post["acta_inspeccion_item"]:
            raise ApplyAbortError("acta_inspeccion_item changed unexpectedly")
        cascade_deleted["acta_inspeccion_item"] = 0

        _verify_preserved_docs(conn, preserved)

        for ot_id in entity_sets["orden_trabajo"]:
            refs = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
            if refs:
                raise ApplyAbortError(f"OT {ot_id} still has acts")

        explicit_deleted["relevamiento"] = _delete_ids(
            conn, "relevamiento", entity_sets["relevamiento"]
        )
        if explicit_deleted["relevamiento"] != EXPECTED_RELS:
            raise ApplyAbortError(f"rel deleted {explicit_deleted['relevamiento']} != {EXPECTED_RELS}")

        rr_after = _count(conn, "relevamiento_relevador")
        rr_deleted = rr_before - rr_after
        if rr_deleted != expected_cascades["relevamiento_relevador"]:
            raise ApplyAbortError(f"RR cascade {rr_deleted} != {expected_cascades['relevamiento_relevador']}")
        if rr_after != child_post["relevamiento_relevador"]:
            raise ApplyAbortError(f"RR post {rr_after} != {child_post['relevamiento_relevador']}")
        cascade_deleted["relevamiento_relevador"] = rr_deleted

        for rid in (1, 2):
            if not _scalar(conn, "SELECT COUNT(*) FROM relevador WHERE id = :id", {"id": rid}):
                raise ApplyAbortError(f"relevador {rid} missing")

        qa = audit_otro_relevador_qa(conn)
        if qa.get("relevamiento_ids"):
            raise ApplyAbortError(f"relevador QA still has refs: {qa['relevamiento_ids']}")

        explicit_deleted["orden_trabajo"] = _delete_ids(
            conn, "orden_trabajo", entity_sets["orden_trabajo"]
        )
        if explicit_deleted["orden_trabajo"] != EXPECTED_OT:
            raise ApplyAbortError(f"ot deleted {explicit_deleted['orden_trabajo']} != {EXPECTED_OT}")

        for entity in PHASE2C2B_DELETE_ORDER:
            if _count_ids_exist(conn, entity, entity_sets[entity]):
                raise ApplyAbortError(f"manifest ids remain: {entity}")

        for entity, expected in POST_MAIN.items():
            if _count(conn, entity) != expected:
                raise ApplyAbortError(f"post {entity}: {_count(conn, entity)} != {expected}")

        for tbl, expected in child_post.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"post child {tbl}: {_count(conn, tbl)} != {expected}")

        for tbl, expected in UNCHANGED_TABLES.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"unchanged {tbl}: {_count(conn, tbl)} != {expected}")

        if _count_ids_exist(conn, "actuaciones", blocked_38) != 38:
            raise ApplyAbortError("blocked acts not preserved")
        if _count_ids_exist(conn, "notificacion", orphan_ids["notificacion"]) != 36:
            raise ApplyAbortError("orphan notifs not preserved")
        if _count_ids_exist(conn, "comprobacion", orphan_ids["comprobacion"]) != 20:
            raise ApplyAbortError("orphan comps not preserved")
        if _count_ids_exist(conn, "notificacion", source_notif_ids) != len(source_notif_ids):
            raise ApplyAbortError("source notifs not preserved")

        protected_preserved: dict[str, Any] = {}
        for entity, min_count in PROTECTED_POSTCONDITION_MIN.items():
            table = _table_for_entity(entity)
            ids = prot.get(entity, set())
            found = _count_ids_exist(conn, table, ids)
            protected_preserved[entity] = {"expected": len(ids), "found": found}
            if found != len(ids):
                raise ApplyAbortError(f"protected {entity}: {found} != {len(ids)}")
            if found < min_count:
                raise ApplyAbortError(f"protected min {entity}: {found} < {min_count}")

        orphans = check_fk_orphans(conn, ORPHAN_TABLES)
        if orphans:
            raise ApplyAbortError(f"orphans: {orphans[:5]}")

        trans.commit()
        committed = True
        status = "COMMITTED"
    except Exception as exc:
        trans.rollback()
        committed = False
        status = "ROLLED_BACK"
        raise ApplyAbortError(str(exc)) from exc

    counts_after = {t: _count(conn, t) for t in list(POST_MAIN) + list(CHILD_TABLES)}
    for t in UNCHANGED_TABLES:
        counts_after[t] = _count(conn, t)

    users_unlock = post_commit_user_analysis(conn)
    catalog_effects = post_commit_catalog_effects(conn)

    return {
        "ticket": "PREDEPLOY-CLEANUP.3G.2",
        "applied_at": datetime.now().isoformat(),
        "database": confirm_database,
        "alembic_revision": preflight["baseline"]["alembic_revision"],
        "freeze_method": freeze_method,
        "manifest_path": str(execution_manifest.get("_source_path", "")),
        "manifest_sha256": expected_exec_hash,
        "source_diag_sha256": expected_source_diag_hash,
        "cascade_reconcile_sha256": expected_cascade_hash,
        "protected_manifest_sha256": expected_prot_hash,
        "backup": {
            "path": backup_path,
            "size": backup_size,
            "sha256": backup_hash,
            "restore_verified": restore_verified,
        },
        "restore_verify": {"verified": restore_verified},
        "counts_before": counts_before,
        "explicit_deleted": explicit_deleted,
        "cascade_deleted": cascade_deleted,
        "preserved": {
            "parent_notificaciones": sorted(preserved["notificacion"]),
            "parent_comprobaciones": sorted(preserved["comprobacion"]),
            "comprobacion_2129": SOURCE_COMP,
            "oficio_1575": SOURCE_OFICIO,
            "blocked_acts_38": sorted(blocked_38),
            "orphan_notificaciones_36": sorted(orphan_ids["notificacion"]),
            "orphan_comprobaciones_20": sorted(orphan_ids["comprobacion"]),
            "source_notificaciones_119": sorted(source_notif_ids),
        },
        "counts_after": counts_after,
        "manifest_ids_remaining": {e: 0 for e in PHASE2C2B_DELETE_ORDER},
        "protected_preserved": protected_preserved,
        "orphan_checks": orphans,
        "users_unlock": users_unlock,
        "catalog_effects": catalog_effects,
        "otro_relevador_qa_post": {
            **qa,
            "status": "READY_FOR_PHASE2E",
        },
        "preflight": preflight,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "phase2c2c_executed": False,
        "phase2e_executed": False,
    }


def post_commit_user_analysis(conn: Connection) -> dict[str, Any]:
    """Recalcula users test FK-free tras FASE 2C.2B."""
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    fk_columns = load_user_fk_columns(conn)
    unlocked: list[int] = []
    still_blocked: list[int] = []
    for uid in test_users:
        refs = []
        for table, col in fk_columns:
            n = _scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE `{col}` = :uid", {"uid": uid})
            if n:
                refs.append(table)
        if not refs:
            unlocked.append(uid)
        else:
            still_blocked.append(uid)
    return {
        "users_test_fk_free_after_2c2b": len(unlocked),
        "users_test_still_blocked": len(still_blocked),
        "unlocked_sample": sorted(unlocked)[:40],
    }


def post_commit_catalog_effects(conn: Connection) -> dict[str, Any]:
    """Metadata post-commit de catálogos (sin DELETE)."""
    qa = audit_otro_relevador_qa(conn)
    rubro_refs = _scalar(
        conn,
        """
        SELECT COUNT(*) FROM relevamiento r
        JOIN rubro rb ON rb.id = r.rubro_id
        WHERE rb.nombre LIKE '%TEST%' OR rb.nombre LIKE '%QA%'
        """,
    )
    return {
        "otro_relevador_qa": qa,
        "rubros_test_relevamiento_refs": int(rubro_refs or 0),
        "policy": "NO_DELETE catalogos en 2C.2B",
    }
