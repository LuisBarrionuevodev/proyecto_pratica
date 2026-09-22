"""Aplicación FASE 2D USERS: DELETE 833 CONFIRMADO_TEST_FK_FREE (transacción única)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.apply_service import (
    ApplyAbortError,
    _assert_admin_and_fabian,
    audit_table_engines,
)
from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.manifest_io import entity_ids, manifest_sha256, validate_ids_exist
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    _known_test_guard,
    _load_known_test_ids_from_manifests,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    _table_for_entity,
    protection_closure_check,
)
from app.domains.predeploy_cleanup.users_phase2d_diag import load_all_user_foreign_keys
from app.domains.predeploy_cleanup.users_phase2d_manifest_freeze import (
    BASELINE_POST_3K2,
    CLASSIFICATION_EXPECTED,
    EXPECTED_BLOCKED,
    EXPECTED_FK_BLOCKED,
    EXPECTED_FK_FREE,
    EXPECTED_SAFE,
    EXPECTED_USERS_AFTER,
    EXPECTED_USERS_TOTAL,
    PRESERVE_USER_IDS,
    REAL_USER_IDS,
    SYSTEM_USER_IDS,
    _admin_graph_guard,
    _baseline_check,
    _build_identity_snapshot,
    _juzgado_922_guard,
    _route_residual_guard,
    _validate_safe_fk_refs,
    _validate_user1,
)

EXPECTED_EXEC_HASH = "f0cd0e7c1a2fe7f55bcc3d3caea4999437e1b23d4131362b3f4b66ff4dd302fa"
EXPECTED_SOURCE_DIAG_HASH = "aa9c0e9db195477392d4da2d778480618ab92e33807ed4d9c6bf38a2565f43ae"
EXPECTED_IDENTITY_HASH = "597c4b3e4d5b84057ec58c3fe11a4cc33d5c23bc33d36510202470527afaa8f3"
EXPECTED_PROT_HASH = "d8a1fda3a10e46dcdb90b22038d73e1e08c76754a59c96dc11cff4377a3b102e"

UNCHANGED_TABLES = {k: v for k, v in BASELINE_POST_3K2.items() if k != "users"}

PROTECTED_POSTCONDITION_MIN = {
    "actuaciones": 1189,
    "orden_trabajo": 1176,
    "inspeccion": 170,
    "notificacion": 168,
    "comprobacion": 56,
    "oficio": 40,
    "expediente": 40,
}

USER_FK_CHILD_TABLES = (
    "denuncia",
    "establecimiento_operativo",
    "iniciador_ruta",
    "password_reset_codes",
    "profiles",
    "relevamiento",
    "ruta_grupo",
    "ruta_grupo_inspector",
    "ruta_item",
    "ruta_pool_dia",
    "ruta_trabajo",
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


def _load_safe_user_ids(execution_manifest: dict[str, Any]) -> set[int]:
    ids = entity_ids(execution_manifest, "users")
    if len(ids) != EXPECTED_SAFE:
        raise ApplyAbortError(f"users count {len(ids)} != {EXPECTED_SAFE}")
    if len(ids) != len(set(ids)):
        raise ApplyAbortError("duplicate safe user IDs in manifest")
    frozen = set(execution_manifest.get("entities", {}).get("users", []))
    if frozen != ids:
        raise ApplyAbortError("entity_ids != manifest entities.users")
    return ids


def _load_blocked_ids(execution_manifest: dict[str, Any]) -> set[int]:
    blocked = set(execution_manifest.get("preserve", {}).get("blocked_test_user_ids", []))
    if len(blocked) != EXPECTED_BLOCKED:
        raise ApplyAbortError(f"blocked count {len(blocked)} != {EXPECTED_BLOCKED}")
    return blocked


def check_user_fk_orphans(conn: Connection, fk_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filas hijas con FK a users cuyo padre ya no existe."""
    orphans: list[dict[str, Any]] = []
    for edge in fk_edges:
        tbl = edge["child_table"]
        col = edge["child_column"]
        cnt = int(
            _scalar(
                conn,
                f"""
                SELECT COUNT(*) FROM `{tbl}` c
                LEFT JOIN users u ON c.`{col}` = u.id
                WHERE c.`{col}` IS NOT NULL AND u.id IS NULL
                """,
            )
            or 0
        )
        if cnt:
            orphans.append(
                {
                    "child_table": tbl,
                    "child_column": col,
                    "orphan_count": cnt,
                }
            )
    return orphans


def _reconcile_fk_free_blocked(conn: Connection, fk_edges: list[dict[str, Any]]) -> dict[str, Any]:
    """Recalcula FK-free / FK-blocked sobre survivors."""
    all_ids = _fetch_ids(conn, "SELECT id FROM users")
    fk_free: set[int] = set()
    fk_blocked: set[int] = set()
    for uid in all_ids:
        has_ref = False
        for edge in fk_edges:
            tbl = edge["child_table"]
            col = edge["child_column"]
            cnt = int(
                _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = :uid", {"uid": uid}) or 0
            )
            if cnt:
                has_ref = True
                break
        if has_ref:
            fk_blocked.add(uid)
        else:
            fk_free.add(uid)

    fk_free_real = fk_free & REAL_USER_IDS
    residual_test_fk_free = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}") & fk_free

    return {
        "fk_free_count": len(fk_free),
        "fk_blocked_count": len(fk_blocked),
        "expected_fk_free": 4,
        "expected_fk_blocked": EXPECTED_FK_BLOCKED,
        "fk_free_real_whitelist_ids": sorted(fk_free_real),
        "residual_test_fk_free_count": len(residual_test_fk_free),
        "residual_test_fk_free_ids": sorted(residual_test_fk_free)[:20],
        "valid": (
            len(fk_free) == 4
            and len(fk_blocked) == EXPECTED_FK_BLOCKED
            and len(residual_test_fk_free) == 0
            and fk_free.issubset(REAL_USER_IDS)
            and len(fk_free_real) == 4
        ),
    }


def preflight_users_phase2d_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_identity_hash: str,
    expected_prot_hash: str,
    backup_confirmed: bool = False,
    manifest_paths: list | None = None,
) -> dict[str, Any]:
    """Preflight FASE 2D USERS antes de BEGIN."""
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
    if execution_manifest.get("identity_snapshot_hash") != expected_identity_hash:
        errors.append("identity_snapshot_hash mismatch")

    closure: dict[str, Any] = {}
    test_guard: dict[str, Any] = {}
    route_guard: dict[str, Any] = {}
    admin_guard: dict[str, Any] = {}
    juzgado_guard: dict[str, Any] = {}
    user1: dict[str, Any] = {}
    fk_validation: dict[str, Any] = {}
    identity: dict[str, Any] = {}
    classification_before: dict[str, Any] = {}

    try:
        baseline = _baseline_check(conn)
        safe_ids = _load_safe_user_ids(execution_manifest)
        blocked_ids = _load_blocked_ids(execution_manifest)

        if safe_ids & PRESERVE_USER_IDS:
            errors.append("SAFE ∩ PRESERVE != 0")
        if safe_ids & blocked_ids:
            errors.append("SAFE ∩ BLOCKED != 0")

        stale_safe = validate_ids_exist(conn, "users", safe_ids, label="users")
        if stale_safe:
            errors.append(f"missing safe users: {stale_safe[:3]}")

        preserve_found = _count_ids_exist(conn, "users", PRESERVE_USER_IDS)
        if preserve_found != len(PRESERVE_USER_IDS):
            errors.append(f"preserve present {preserve_found}/14")

        blocked_found = _count_ids_exist(conn, "users", blocked_ids)
        if blocked_found != EXPECTED_BLOCKED:
            errors.append(f"blocked present {blocked_found}/{EXPECTED_BLOCKED}")

        identity = _build_identity_snapshot(conn, sorted(safe_ids))
        if identity["identity_snapshot_hash"] != expected_identity_hash:
            errors.append("identity snapshot hash drift")
        if identity["active_true"] != EXPECTED_SAFE or identity["active_false"] != 0:
            errors.append("active distribution drift")

        fk_edges = load_all_user_foreign_keys(conn)
        if len(fk_edges) != 12:
            errors.append(f"fk edge count {len(fk_edges)} != 12")

        fk_validation = _validate_safe_fk_refs(conn, safe_ids, fk_edges)
        if not fk_validation.get("valid"):
            errors.append("SAFE FK refs != 0")

        user1 = _validate_user1(conn)
        if user1["user_id"] in safe_ids:
            errors.append("user 1 in safe set")

        prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
        virtual = VirtualDeleteState()
        virtual.add_explicit("users", safe_ids)
        closure = protection_closure_check(virtual, prot)
        if not closure.get("valid"):
            errors.append("protected closure failed")

        if manifest_paths:
            known = _load_known_test_ids_from_manifests(manifest_paths)
            test_guard = _known_test_guard(conn, known)
            if not test_guard["guard_ok"]:
                errors.append(
                    f"known test guard acts={test_guard['known_test_act_ids_remaining_count']}"
                )

        route_guard = _route_residual_guard(conn)
        if not route_guard["guard_ok"]:
            errors.append("route residual guard failed")

        admin_guard = _admin_graph_guard(conn)
        if not admin_guard["guard_ok"]:
            errors.append("admin graph guard failed")

        juzgado_guard = _juzgado_922_guard(conn)

        classification_before = {
            "summary": CLASSIFICATION_EXPECTED,
            "fk_free_current": EXPECTED_FK_FREE,
            "fk_blocked_current": EXPECTED_FK_BLOCKED,
            "reconciliation": (
                "837 FK-free = 833 SAFE + 4 real whitelist; "
                "1966 FK-blocked = 1956 test blocked + 10 preserve non-test"
            ),
        }

    except Exception as exc:
        errors.append(str(exc))
        baseline = {}

    engine_audit = audit_table_engines(conn, ("users",))
    if not engine_audit["apply_enabled"]:
        errors.append(f"non-InnoDB: {engine_audit['non_transactional']}")

    try:
        _assert_admin_and_fabian(conn)
    except ApplyAbortError as exc:
        errors.append(str(exc))

    if errors:
        raise ApplyAbortError("; ".join(errors))

    return {
        "status": "PHASE2D_PREFLIGHT_OK",
        "baseline": baseline,
        "safe_users_count": EXPECTED_SAFE,
        "identity_snapshot_hash": identity["identity_snapshot_hash"],
        "fk_schema_edge_count": 12,
        "safe_fk_validation": fk_validation,
        "protected_closure": closure,
        "known_test_guards": test_guard,
        "route_residual_guard": route_guard,
        "admin_graph_guard": admin_guard,
        "juzgado_922_guard": juzgado_guard,
        "user1_guard": user1,
        "classification_before": classification_before,
    }


def apply_users_phase2d_cleanup(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_identity_hash: str,
    expected_prot_hash: str,
    backup_path: str,
    backup_hash: str,
    backup_size: int,
    restore_verified: bool,
    freeze_method: str,
    manifest_paths: list | None = None,
) -> dict[str, Any]:
    """Aplica DELETE FASE 2D USERS en transacción única."""
    safe_ids = _load_safe_user_ids(execution_manifest)
    blocked_ids = _load_blocked_ids(execution_manifest)
    fk_edges = load_all_user_foreign_keys(conn)

    counts_before = dict(BASELINE_POST_3K2)
    profiles_before = _count(conn, "profiles")
    prc_before = _count(conn, "password_reset_codes")

    preflight = preflight_users_phase2d_apply(
        conn,
        execution_manifest,
        protected_manifest,
        expected_exec_hash=expected_exec_hash,
        expected_source_diag_hash=expected_source_diag_hash,
        expected_identity_hash=expected_identity_hash,
        expected_prot_hash=expected_prot_hash,
        backup_confirmed=True,
        manifest_paths=manifest_paths,
    )

    if not restore_verified:
        raise ApplyAbortError("restore_verified required")

    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))

    if conn.in_transaction():
        conn.rollback()

    explicit_deleted: dict[str, int] = {}
    trans = conn.begin()
    orphans: list[dict[str, Any]] = []
    protected_preserved: dict[str, Any] = {}
    user1_post: dict[str, Any] = {}
    fk_after: dict[str, Any] = {}

    try:
        explicit_deleted["users"] = _delete_ids(conn, "users", safe_ids)
        if explicit_deleted["users"] != EXPECTED_SAFE:
            raise ApplyAbortError(
                f"users deleted {explicit_deleted['users']} != {EXPECTED_SAFE}"
            )

        remaining_safe = _count_ids_exist(conn, "users", safe_ids)
        if remaining_safe != 0:
            raise ApplyAbortError(f"manifest safe ids remaining: {remaining_safe}")

        profiles_after = _count(conn, "profiles")
        prc_after = _count(conn, "password_reset_codes")
        if profiles_after != profiles_before:
            raise ApplyAbortError(f"profiles changed: {profiles_before} -> {profiles_after}")
        if prc_after != prc_before:
            raise ApplyAbortError(f"password_reset_codes changed: {prc_before} -> {prc_after}")

        if _count(conn, "users") != EXPECTED_USERS_AFTER:
            raise ApplyAbortError(f"post users: {_count(conn, 'users')}")

        if _count_ids_exist(conn, "users", blocked_ids) != EXPECTED_BLOCKED:
            raise ApplyAbortError("blocked test users not all preserved")
        if _count_ids_exist(conn, "users", REAL_USER_IDS) != len(REAL_USER_IDS):
            raise ApplyAbortError("real users not all preserved")
        if not _scalar(conn, "SELECT COUNT(*) FROM users WHERE id = 1"):
            raise ApplyAbortError("user 1 missing post-delete")

        for tbl, expected in UNCHANGED_TABLES.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"unchanged {tbl}: {_count(conn, tbl)} != {expected}")

        for entity, min_count in PROTECTED_POSTCONDITION_MIN.items():
            table = _table_for_entity(entity)
            ids = prot.get(entity, set())
            found = _count_ids_exist(conn, table, ids)
            protected_preserved[entity] = {"expected": len(ids), "found": found}
            if found != len(ids):
                raise ApplyAbortError(f"protected {entity}: {found} != {len(ids)}")
            if found < min_count:
                raise ApplyAbortError(f"protected min {entity}: {found} < {min_count}")

        orphans = check_user_fk_orphans(conn, fk_edges)
        if orphans:
            raise ApplyAbortError(f"user FK orphans: {orphans[:5]}")

        user1_post = _validate_user1(conn)
        fk_after = _reconcile_fk_free_blocked(conn, fk_edges)
        if not fk_after["valid"]:
            raise ApplyAbortError(f"fk post reconciliation: {fk_after}")

        juzgado_post = _juzgado_922_guard(conn)

        trans.commit()
        committed = True
        status = "COMMITTED"
    except Exception as exc:
        trans.rollback()
        committed = False
        status = "ROLLED_BACK"
        raise ApplyAbortError(str(exc)) from exc

    counts_after = dict(BASELINE_POST_3K2)
    counts_after["users"] = EXPECTED_USERS_AFTER

    return {
        "ticket": "PREDEPLOY-CLEANUP.3L.2",
        "applied_at": datetime.now().isoformat(),
        "database": confirm_database,
        "alembic_revision": preflight["baseline"]["alembic_revision"],
        "freeze_method": freeze_method,
        "manifest_path": str(execution_manifest.get("_source_path", "")),
        "manifest_sha256": expected_exec_hash,
        "source_diag_sha256": expected_source_diag_hash,
        "protected_manifest_sha256": expected_prot_hash,
        "identity_snapshot_hash": expected_identity_hash,
        "backup": {
            "path": backup_path,
            "size": backup_size,
            "sha256": backup_hash,
            "restore_verified": restore_verified,
        },
        "restore_verify": {"verified": restore_verified},
        "counts_before": counts_before,
        "classification_before": preflight["classification_before"],
        "fk_schema": {
            "edge_count": len(fk_edges),
            "ALL_USER_FOREIGN_KEYS": fk_edges,
        },
        "safe_fk_validation": preflight["safe_fk_validation"],
        "explicit_deleted": explicit_deleted,
        "cascade_deleted": {"profiles": 0, "password_reset_codes": 0, "total": 0},
        "set_null_affected": {"total": 0},
        "counts_after": counts_after,
        "manifest_ids_remaining": {"users": 0},
        "survivor_reconciliation": {
            "blocked_test": EXPECTED_BLOCKED,
            "real": len(REAL_USER_IDS),
            "system": len(SYSTEM_USER_IDS),
            "total": EXPECTED_USERS_AFTER,
        },
        "fk_free_blocked_after": fk_after,
        "real_users_preserved": sorted(REAL_USER_IDS),
        "system_users_preserved": sorted(SYSTEM_USER_IDS),
        "blocked_test_users_preserved_count": EXPECTED_BLOCKED,
        "auth_tables_preserved": {
            "profiles": profiles_before,
            "password_reset_codes": prc_before,
        },
        "protected_preserved": protected_preserved,
        "orphan_checks": orphans,
        "user1_fallback_metadata": {
            "ticket": "AUDIT-CREATED-BY-FALLBACK-PREDEPLOY",
            "before": preflight["user1_guard"],
            "after": user1_post,
        },
        "juzgado_922_guard": juzgado_post,
        "preflight": preflight,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "phase2e_executed": False,
    }
