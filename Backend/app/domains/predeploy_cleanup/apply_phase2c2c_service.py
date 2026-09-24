"""Aplicación FASE 2C.2C: DELETE 36 notificaciones + 20 comprobaciones (transacción única)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.apply_service import (
    ApplyAbortError,
    _assert_admin_and_fabian,
    audit_table_engines,
    check_fk_orphans,
)
from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import entity_ids, manifest_sha256, validate_ids_exist
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.phase2c1_unlocked_sources_diag import _validate_delete_order_fk
from app.domains.predeploy_cleanup.phase2c2b_sources_manifest_freeze import _protected_comp_regression
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    USERS_FK_FREE_POST_3H,
    _known_test_guard,
    _load_known_test_ids_from_manifests,
)
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_manifest_freeze import (
    BASELINE_POST_3H,
    BLOCKED_COMPROBACION_2289,
    BLOCKED_NOTIFICACIONES_25,
    EMPTY_ROUTE_IDS,
    EXPECTED_SAFE_COMP,
    EXPECTED_SAFE_NOTIF,
    PHASE2C2C_DELETE_ORDER,
    POST_EXPLICIT,
    SAFE_COMPROBACIONES_2C2C,
    SAFE_NOTIFICACIONES_2C2C,
    _audit_comprobacion_2289,
    _baseline_check,
    _validate_blocked_notificaciones,
    _validate_cascades_zero,
    _validate_safe_fk_zero,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    _table_for_entity,
    load_user_fk_columns,
    protection_closure_check,
)

EXPECTED_EXEC_HASH = "e7ccb2203424686141a50092cc4f790c903cb697de005d9a08cc5727b0971403"
EXPECTED_SOURCE_DIAG_HASH = "4ae9e4d5d4514e9bc33a6830da8af165a8053bc2163b44f626162495285820c2"
EXPECTED_PROT_HASH = "d8a1fda3a10e46dcdb90b22038d73e1e08c76754a59c96dc11cff4377a3b102e"

FUTURE_EXPEDIENTE_IDS = (
    1972,
    1975,
    1976,
    1985,
    1987,
    2073,
    2074,
    2075,
    2139,
    2140,
    2141,
    2334,
    2761,
    2900,
    2914,
    2942,
    2980,
    2983,
    2991,
    3006,
    3007,
    3008,
    3034,
    3040,
    3044,
    3103,
    3104,
)

FUTURE_OFICIO_IDS = (1662,)

UNCHANGED_TABLES = {k: v for k, v in BASELINE_POST_3H.items() if k not in POST_EXPLICIT}

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
    "notificacion",
    "notificacion_motivo",
    "comprobacion",
    "actuaciones",
    "iniciador_ruta",
    "expediente",
    "oficio",
)

MANIFEST_PATHS_FOR_GUARD = [
    "cleanup_execution_manifest_phase1_20260920.json",
    "cleanup_execution_manifest_phase2c1_sources_20260920.json",
    "cleanup_execution_manifest_phase2c2b_sources_20260920.json",
    "cleanup_execution_manifest_phase2c2b_prime_sources_20260920.json",
]


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
    expected = {"notificacion": EXPECTED_SAFE_NOTIF, "comprobacion": EXPECTED_SAFE_COMP}
    sets: dict[str, set[int]] = {}
    for entity in PHASE2C2C_DELETE_ORDER:
        ids = entity_ids(execution_manifest, entity)
        if len(ids) != expected[entity]:
            raise ApplyAbortError(f"{entity} count {len(ids)} != {expected[entity]}")
        if set(ids) != set(
            SAFE_NOTIFICACIONES_2C2C if entity == "notificacion" else SAFE_COMPROBACIONES_2C2C
        ):
            raise ApplyAbortError(f"{entity} IDs != frozen list")
        sets[entity] = ids
    return sets


def _load_preserved_from_manifest(execution_manifest: dict[str, Any]) -> dict[str, Any]:
    blocked_notif = {int(x) for x in execution_manifest["blocked"]["notificacion"]}
    blocked_comp = {int(x) for x in execution_manifest["blocked"]["comprobacion"]}
    future = execution_manifest.get("future_admin_graph", {})
    exp_ids = {int(x) for x in future.get("expediente_ids_union", [])}
    oficio_ids = {int(x) for x in future.get("oficio_ids", [])}
    source_119_overlap = {
        int(x) for x in execution_manifest.get("source_119_cross", {}).get("candidate_cap_source_119", [])
    }

    if blocked_notif != set(BLOCKED_NOTIFICACIONES_25):
        raise ApplyAbortError("blocked notif mismatch")
    if blocked_comp != {BLOCKED_COMPROBACION_2289}:
        raise ApplyAbortError("blocked comp mismatch")
    if exp_ids != set(FUTURE_EXPEDIENTE_IDS):
        raise ApplyAbortError(f"future expediente mismatch: {sorted(exp_ids)}")
    if oficio_ids != set(FUTURE_OFICIO_IDS):
        raise ApplyAbortError("future oficio mismatch")

    return {
        "blocked_notificaciones_25": blocked_notif,
        "blocked_comprobacion_2289": blocked_comp,
        "future_expediente_ids": exp_ids,
        "future_oficio_ids": oficio_ids,
        "source_119_overlap_15": source_119_overlap,
        "blocked_notif_expediente_links": execution_manifest.get("blocked_notificacion_expediente_links", []),
    }


def _verify_future_admin_graph(conn: Connection, preserved: dict[str, Any]) -> None:
    if _count_ids_exist(conn, "expediente", preserved["future_expediente_ids"]) != len(FUTURE_EXPEDIENTE_IDS):
        raise ApplyAbortError("future expedientes missing")
    if _count_ids_exist(conn, "oficio", preserved["future_oficio_ids"]) != len(FUTURE_OFICIO_IDS):
        raise ApplyAbortError("future oficios missing")
    if not _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id = 1662 AND numero_oficio = 'OF8430'"):
        raise ApplyAbortError("oficio 1662/OF8430 missing")


def _verify_empty_routes(conn: Connection) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for rtid in EMPTY_ROUTE_IDS:
        if not _scalar(conn, "SELECT COUNT(*) FROM ruta_trabajo WHERE id = :id", {"id": rtid}):
            raise ApplyAbortError(f"route {rtid} missing")
        refs = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_trabajo_id = {rtid}")
        if refs:
            raise ApplyAbortError(f"route {rtid} has ruta_item refs")
        routes.append({"ruta_trabajo_id": rtid, "ruta_item_refs": 0})
    return routes


def _verify_source_119_guard(safe_notif: set[int], preserved: dict[str, Any]) -> None:
    if safe_notif & preserved["source_119_overlap_15"]:
        raise ApplyAbortError("safe notif intersects source_119 blocked candidates")


def preflight_phase2c2c_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_prot_hash: str,
    backup_confirmed: bool = False,
    manifest_paths: list | None = None,
) -> dict[str, Any]:
    """Preflight FASE 2C.2C antes de BEGIN."""
    errors: list[str] = []

    if not backup_confirmed:
        errors.append("backup_confirmed required")

    manifest_for_hash = {k: v for k, v in execution_manifest.items() if not k.startswith("_")}
    computed = manifest_sha256(manifest_for_hash)
    if computed != expected_exec_hash:
        errors.append(f"execution hash {computed} != {expected_exec_hash}")
    if execution_manifest.get("source_diag_sha256") != expected_source_diag_hash:
        errors.append("source_diag_sha256 mismatch")
    if execution_manifest.get("protected_manifest_sha256") != expected_prot_hash:
        errors.append("protected_manifest_sha256 mismatch")

    cascade_info: dict[str, Any] = {}
    closure: dict[str, Any] = {}
    test_guard: dict[str, Any] = {}
    comp_reg: dict[str, Any] = {}

    try:
        baseline = _baseline_check(conn)
        entity_sets = _load_entity_sets(execution_manifest)
        preserved = _load_preserved_from_manifest(execution_manifest)
        safe_notif = entity_sets["notificacion"]
        safe_comp = entity_sets["comprobacion"]

        for entity, ids in entity_sets.items():
            stale = validate_ids_exist(conn, entity, ids, label=entity)
            if stale:
                errors.append(f"missing {entity}: {stale[:3]}")

        _validate_safe_fk_zero(conn, "notificacion", safe_notif)
        _validate_safe_fk_zero(conn, "comprobacion", safe_comp)
        cascade_info = _validate_cascades_zero(conn, safe_notif, safe_comp)

        if _count_ids_exist(conn, "notificacion", preserved["blocked_notificaciones_25"]) != 25:
            errors.append("blocked notifs missing")
        _validate_blocked_notificaciones(conn, preserved["blocked_notificaciones_25"])
        _audit_comprobacion_2289(conn)
        _verify_future_admin_graph(conn, preserved)
        _verify_source_119_guard(safe_notif, preserved)
        _verify_empty_routes(conn)

        prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
        if safe_notif & prot.get("notificacion", set()):
            errors.append("protected notif intersection")
        if safe_comp & prot.get("comprobacion", set()):
            errors.append("protected comp intersection")

        virtual = VirtualDeleteState()
        virtual.add_explicit("notificacion", safe_notif)
        virtual.add_explicit("comprobacion", safe_comp)
        closure = protection_closure_check(virtual, prot)
        if not closure.get("valid"):
            errors.append("protected closure failed")

        comp_reg = _protected_comp_regression(conn, prot)
        if not comp_reg["all_protected"]:
            errors.append("protected comprobacion regression")

        fk_valid = _validate_delete_order_fk(PHASE2C2C_DELETE_ORDER, load_fk_edges(conn))
        if not fk_valid.get("valid"):
            errors.append(f"delete order: {fk_valid.get('violations')}")

        if manifest_paths:
            known = _load_known_test_ids_from_manifests(manifest_paths)
            test_guard = _known_test_guard(conn, known)
            if not test_guard["guard_ok"]:
                errors.append(
                    f"known test guard: acts={test_guard['known_test_act_ids_remaining_count']}"
                )

    except Exception as exc:
        errors.append(str(exc))
        baseline = {}

    engine_audit = audit_table_engines(conn, tuple(PHASE2C2C_DELETE_ORDER))
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
        "cascade_preflight": cascade_info,
        "protected_closure": closure,
        "protected_comprobacion_regression": comp_reg,
        "known_test_guards": test_guard,
    }


def apply_phase2c2c_orphan_documents_cleanup(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_prot_hash: str,
    backup_path: str,
    backup_hash: str,
    backup_size: int,
    restore_verified: bool,
    freeze_method: str,
    manifest_paths: list | None = None,
) -> dict[str, Any]:
    """Aplica DELETE FASE 2C.2C en transacción única."""
    entity_sets = _load_entity_sets(execution_manifest)
    preserved = _load_preserved_from_manifest(execution_manifest)
    safe_notif = entity_sets["notificacion"]
    safe_comp = entity_sets["comprobacion"]

    counts_before = {t: _count(conn, t) for t in list(POST_EXPLICIT) + list(UNCHANGED_TABLES)}

    preflight = preflight_phase2c2c_apply(
        conn,
        execution_manifest,
        protected_manifest,
        confirm_database=confirm_database,
        expected_exec_hash=expected_exec_hash,
        expected_source_diag_hash=expected_source_diag_hash,
        expected_prot_hash=expected_prot_hash,
        backup_confirmed=True,
        manifest_paths=manifest_paths,
    )

    if not restore_verified:
        raise ApplyAbortError("restore_verified required")

    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    notif_motivo_before = _count(conn, "notificacion_motivo")

    if conn.in_transaction():
        conn.rollback()

    explicit_deleted: dict[str, int] = {}
    cascade_deleted: dict[str, int] = {"notificacion_motivo": 0}
    set_null_affected: dict[str, int] = {}
    trans = conn.begin()
    try:
        explicit_deleted["notificacion"] = _delete_ids(conn, "notificacion", safe_notif)
        if explicit_deleted["notificacion"] != EXPECTED_SAFE_NOTIF:
            raise ApplyAbortError(
                f"notif deleted {explicit_deleted['notificacion']} != {EXPECTED_SAFE_NOTIF}"
            )
        if _count_ids_exist(conn, "notificacion", safe_notif):
            raise ApplyAbortError("notif manifest ids remain")

        notif_motivo_after = _count(conn, "notificacion_motivo")
        cascade_deleted["notificacion_motivo"] = notif_motivo_before - notif_motivo_after
        if cascade_deleted["notificacion_motivo"] != 0:
            raise ApplyAbortError(f"notificacion_motivo cascade {cascade_deleted['notificacion_motivo']}")

        if _count(conn, "notificacion") != POST_EXPLICIT["notificacion"]:
            raise ApplyAbortError(f"post notif: {_count(conn, 'notificacion')}")

        if _count_ids_exist(conn, "notificacion", preserved["blocked_notificaciones_25"]) != 25:
            raise ApplyAbortError("blocked notifs not preserved after notif delete")
        _validate_blocked_notificaciones(conn, preserved["blocked_notificaciones_25"])
        _verify_future_admin_graph(conn, preserved)

        explicit_deleted["comprobacion"] = _delete_ids(conn, "comprobacion", safe_comp)
        if explicit_deleted["comprobacion"] != EXPECTED_SAFE_COMP:
            raise ApplyAbortError(
                f"comp deleted {explicit_deleted['comprobacion']} != {EXPECTED_SAFE_COMP}"
            )
        if _count_ids_exist(conn, "comprobacion", safe_comp):
            raise ApplyAbortError("comp manifest ids remain")

        if not _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": 2289}):
            raise ApplyAbortError("comprobacion 2289 missing after comp delete")
        _audit_comprobacion_2289(conn)

        for tbl, expected in POST_EXPLICIT.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"post {tbl}: {_count(conn, tbl)} != {expected}")

        for tbl, expected in UNCHANGED_TABLES.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"unchanged {tbl}: {_count(conn, tbl)} != {expected}")

        empty_routes = _verify_empty_routes(conn)
        _verify_future_admin_graph(conn, preserved)

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

    counts_after = {t: _count(conn, t) for t in list(POST_EXPLICIT) + list(UNCHANGED_TABLES)}
    users_unlock = post_commit_user_analysis(conn)

    known_guard = preflight.get("known_test_guards", {})

    return {
        "ticket": "PREDEPLOY-CLEANUP.3I.2",
        "applied_at": datetime.now().isoformat(),
        "database": confirm_database,
        "alembic_revision": preflight["baseline"]["alembic_revision"],
        "freeze_method": freeze_method,
        "manifest_path": str(execution_manifest.get("_source_path", "")),
        "manifest_sha256": expected_exec_hash,
        "source_diag_sha256": expected_source_diag_hash,
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
        "cascade_deleted": {**cascade_deleted, "total": sum(cascade_deleted.values())},
        "set_null_affected": {**set_null_affected, "total": sum(set_null_affected.values())},
        "counts_after": counts_after,
        "manifest_ids_remaining": {e: 0 for e in PHASE2C2C_DELETE_ORDER},
        "blocked_preserved": {
            "notificaciones_25": sorted(preserved["blocked_notificaciones_25"]),
            "comprobacion_2289": BLOCKED_COMPROBACION_2289,
        },
        "future_admin_graph_preserved": {
            "expedientes_27": sorted(preserved["future_expediente_ids"]),
            "oficio_1662": 1662,
            "classification": "FUTURE_ADMIN_GRAPH_CANDIDATE",
        },
        "source_119_guard": {
            "safe_cap_source_119": 0,
            "candidate_cap_source_119": sorted(preserved["source_119_overlap_15"]),
        },
        "known_test_guards": known_guard,
        "empty_routes_residual": empty_routes,
        "protected_preserved": protected_preserved,
        "orphan_checks": orphans,
        "users_unlock": users_unlock,
        "preflight": preflight,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "route_residual_cleanup_executed": False,
        "admin_graph_cleanup_executed": False,
        "phase2d_executed": False,
        "phase2e_executed": False,
    }


def post_commit_user_analysis(conn: Connection) -> dict[str, Any]:
    """Recalcula users test FK-free tras FASE 2C.2C."""
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    fk_columns = load_user_fk_columns(conn)
    deleted_docs = set(SAFE_NOTIFICACIONES_2C2C) | set(SAFE_COMPROBACIONES_2C2C)
    unlocked: list[int] = []
    still_blocked: list[int] = []
    for uid in test_users:
        refs = []
        for table, col in fk_columns:
            for r in conn.execute(text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}):
                if table in ("notificacion", "comprobacion") and r[0] in deleted_docs:
                    continue
                refs.append(table)
                break
            if refs:
                break
        if not refs:
            unlocked.append(uid)
        else:
            still_blocked.append(uid)
    return {
        "users_test_fk_free_baseline_post_3h": USERS_FK_FREE_POST_3H,
        "users_test_fk_free_after_2c2c": len(unlocked),
        "users_additionally_unlocked": len(unlocked) - USERS_FK_FREE_POST_3H,
        "users_test_still_blocked": len(still_blocked),
    }
