"""Aplicación ROUTE-RESIDUAL: DELETE 12 ruta_trabajo (transacción única)."""

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
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    _known_test_guard,
    _load_known_test_ids_from_manifests,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.route_residual_diag import _admin_graph_guard
from app.domains.predeploy_cleanup.route_residual_manifest_freeze import (
    BASELINE_POST_3I2,
    EXPECTED_SAFE_ROUTES,
    POST_EXPLICIT,
    PROVENANCE_ROUTE_TO_ITEM_ACT,
    ROUTE_RESIDUAL_DELETE_ORDER,
    SAFE_RUTA_TRABAJO_RESIDUAL,
    USERS_FK_FREE_POST_3I,
    _baseline_check_extended,
    _validate_child_physical_rows,
    _validate_operational_empty,
    _validate_provenance,
    load_deleted_item_provenance,
)
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    _table_for_entity,
    load_user_fk_columns,
    protection_closure_check,
)

EXPECTED_EXEC_HASH = "078b6806096dae16837cf5ff6616aff42a8f9d0723fe61133f13273658dd484b"
EXPECTED_SOURCE_DIAG_HASH = "b811a6bb7536c65935cf6a0b3ba9af8e4482bd6f34f508fa8643bcfb3f4c33e8"
EXPECTED_PROT_HASH = "d8a1fda3a10e46dcdb90b22038d73e1e08c76754a59c96dc11cff4377a3b102e"

UNCHANGED_TABLES = {k: v for k, v in BASELINE_POST_3I2.items() if k != "ruta_trabajo"}

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
    "ruta_trabajo",
    "ruta_grupo",
    "ruta_grupo_inspector",
    "ruta_item",
    "ruta_pool_dia",
    "iniciador_ruta",
)

CHILD_TABLES = ("ruta_grupo", "ruta_grupo_inspector", "ruta_item", "ruta_pool_dia")


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


def _load_route_ids(execution_manifest: dict[str, Any]) -> set[int]:
    ids = entity_ids(execution_manifest, "ruta_trabajo")
    if len(ids) != EXPECTED_SAFE_ROUTES:
        raise ApplyAbortError(f"ruta_trabajo count {len(ids)} != {EXPECTED_SAFE_ROUTES}")
    if set(ids) != set(SAFE_RUTA_TRABAJO_RESIDUAL):
        raise ApplyAbortError("route IDs != frozen list")
    return ids


def preflight_route_residual_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    prime_manifest_path,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_prot_hash: str,
    backup_confirmed: bool = False,
    manifest_paths: list | None = None,
) -> dict[str, Any]:
    """Preflight ROUTE-RESIDUAL antes de BEGIN."""
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

    closure: dict[str, Any] = {}
    test_guard: dict[str, Any] = {}

    try:
        baseline = _baseline_check_extended(conn)
        route_ids = _load_route_ids(execution_manifest)
        stale = validate_ids_exist(conn, "ruta_trabajo", route_ids, label="ruta_trabajo")
        if stale:
            errors.append(f"missing routes: {stale[:3]}")

        prime_prov = load_deleted_item_provenance(prime_manifest_path)
        _validate_provenance(prime_prov, route_ids)
        for rtid in sorted(route_ids):
            _validate_operational_empty(conn, rtid)
        _validate_child_physical_rows(conn, route_ids)

        prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
        if route_ids & prot.get("ruta_trabajo", set()):
            errors.append("protected ruta_trabajo intersection")

        virtual = VirtualDeleteState()
        virtual.add_explicit("ruta_trabajo", route_ids)
        closure = protection_closure_check(virtual, prot)
        if not closure.get("valid"):
            errors.append("protected closure failed")

        admin = _admin_graph_guard(conn)
        if admin["blocked_notificaciones_25_present"] != 25:
            errors.append("admin blocked notifs")
        if not admin["comprobacion_2289_present"]:
            errors.append("comp 2289 missing")
        if admin["future_expedientes_27_present"] != 27:
            errors.append("expedientes 27 missing")
        if not admin["oficio_1662_present"]:
            errors.append("oficio 1662 missing")

        fk_valid = _validate_delete_order_fk(ROUTE_RESIDUAL_DELETE_ORDER, load_fk_edges(conn))
        if not fk_valid.get("valid"):
            errors.append(f"delete order: {fk_valid.get('violations')}")

        if manifest_paths:
            known = _load_known_test_ids_from_manifests(manifest_paths)
            test_guard = _known_test_guard(conn, known)
            if not test_guard["guard_ok"]:
                errors.append(
                    f"known test guard acts={test_guard['known_test_act_ids_remaining_count']}"
                )

    except Exception as exc:
        errors.append(str(exc))
        baseline = {}

    engine_audit = audit_table_engines(conn, tuple(ROUTE_RESIDUAL_DELETE_ORDER))
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
        "protected_closure": closure,
        "known_test_guards": test_guard,
        "admin_graph_guard": admin,
    }


def apply_route_residual_cleanup(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    prime_manifest_path,
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
    """Aplica DELETE ROUTE-RESIDUAL en transacción única."""
    route_ids = _load_route_ids(execution_manifest)
    counts_before = {t: _count(conn, t) for t in list(POST_EXPLICIT) + list(UNCHANGED_TABLES)}

    preflight = preflight_route_residual_apply(
        conn,
        execution_manifest,
        protected_manifest,
        prime_manifest_path=prime_manifest_path,
        expected_exec_hash=expected_exec_hash,
        expected_source_diag_hash=expected_source_diag_hash,
        expected_prot_hash=expected_prot_hash,
        backup_confirmed=True,
        manifest_paths=manifest_paths,
    )

    if not restore_verified:
        raise ApplyAbortError("restore_verified required")

    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    child_before = {t: _count(conn, t) for t in CHILD_TABLES}

    if conn.in_transaction():
        conn.rollback()

    explicit_deleted: dict[str, int] = {}
    cascade_deleted = {
        "ruta_grupo": 0,
        "ruta_grupo_inspector": 0,
        "ruta_item": 0,
    }
    set_null_affected = {"ruta_pool_dia": 0}
    trans = conn.begin()
    try:
        explicit_deleted["ruta_trabajo"] = _delete_ids(conn, "ruta_trabajo", route_ids)
        if explicit_deleted["ruta_trabajo"] != EXPECTED_SAFE_ROUTES:
            raise ApplyAbortError(
                f"routes deleted {explicit_deleted['ruta_trabajo']} != {EXPECTED_SAFE_ROUTES}"
            )
        if _count_ids_exist(conn, "ruta_trabajo", route_ids):
            raise ApplyAbortError("route manifest ids remain")

        for tbl in ("ruta_grupo", "ruta_item", "ruta_grupo_inspector"):
            after = _count(conn, tbl)
            deleted_n = child_before[tbl] - after
            cascade_deleted[tbl] = deleted_n
            if deleted_n != 0:
                raise ApplyAbortError(f"cascade {tbl}: {deleted_n}")

        pool_null_count = int(
            _scalar(
                conn,
                f"""
                SELECT COUNT(*) FROM ruta_pool_dia
                WHERE ruta_trabajo_id IN ({','.join(str(i) for i in sorted(route_ids))})
                """,
            )
            or 0
        )
        if pool_null_count != 0:
            raise ApplyAbortError(f"pool not set null as expected: {pool_null_count}")

        pool_after = _count(conn, "ruta_pool_dia")
        if pool_after != child_before["ruta_pool_dia"]:
            set_null_affected["ruta_pool_dia"] = child_before["ruta_pool_dia"] - pool_after
            if set_null_affected["ruta_pool_dia"] != 0:
                raise ApplyAbortError(f"pool set null: {set_null_affected['ruta_pool_dia']}")

        if _count(conn, "ruta_trabajo") != POST_EXPLICIT["ruta_trabajo"]:
            raise ApplyAbortError(f"post ruta_trabajo: {_count(conn, 'ruta_trabajo')}")

        for tbl, expected in UNCHANGED_TABLES.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"unchanged {tbl}: {_count(conn, tbl)} != {expected}")

        admin = _admin_graph_guard(conn)
        if admin["blocked_notificaciones_25_present"] != 25:
            raise ApplyAbortError("post: blocked notifs")
        if not admin["comprobacion_2289_present"]:
            raise ApplyAbortError("post: comp 2289")
        if admin["future_expedientes_27_present"] != 27:
            raise ApplyAbortError("post: expedientes")
        if not admin["oficio_1662_present"]:
            raise ApplyAbortError("post: oficio 1662")

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

    return {
        "ticket": "PREDEPLOY-CLEANUP.3J.2",
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
        "manifest_ids_remaining": {"ruta_trabajo": 0},
        "admin_graph_preserved": preflight["admin_graph_guard"],
        "known_test_guards": preflight.get("known_test_guards", {}),
        "protected_preserved": protected_preserved,
        "orphan_checks": orphans,
        "users_unlock": users_unlock,
        "provenance_frozen": [
            {"ruta_trabajo_id": rtid, **PROVENANCE_ROUTE_TO_ITEM_ACT[rtid]}
            for rtid in sorted(route_ids)
        ],
        "preflight": preflight,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "admin_graph_cleanup_executed": False,
        "phase2d_executed": False,
        "phase2e_executed": False,
    }


def post_commit_user_analysis(conn: Connection) -> dict[str, Any]:
    """Recalcula users test FK-free tras ROUTE-RESIDUAL."""
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    fk_columns = load_user_fk_columns(conn)
    deleted_routes = set(SAFE_RUTA_TRABAJO_RESIDUAL)
    unlocked = 0
    still = 0
    for uid in test_users:
        blocked = False
        for table, col in fk_columns:
            for r in conn.execute(text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}):
                if table == "ruta_trabajo" and r[0] in deleted_routes:
                    continue
                blocked = True
                break
            if blocked:
                break
        if blocked:
            still += 1
        else:
            unlocked += 1
    return {
        "users_test_fk_free_baseline_post_3i": USERS_FK_FREE_POST_3I,
        "users_test_fk_free_after_route_cleanup": unlocked,
        "users_additionally_unlocked": unlocked - USERS_FK_FREE_POST_3I,
        "users_test_still_blocked": still,
    }
