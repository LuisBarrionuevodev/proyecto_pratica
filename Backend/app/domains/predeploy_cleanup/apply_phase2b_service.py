"""Aplicación FASE 2B: DELETE rutas residuales + iniciadores test (transacción única)."""

from __future__ import annotations

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
from app.domains.predeploy_cleanup.constants import (
    RELEVAMIENTOS_QA_IDS,
    SQL_TEST_USER_WHERE,
)
from app.domains.predeploy_cleanup.manifest_io import (
    entity_ids,
    manifest_sha256,
    validate_ids_exist,
)
from app.domains.predeploy_cleanup.phase2_blockers_diag import _blocked_act_ids
from app.domains.predeploy_cleanup.phase2b_routes_initiators_diag import load_structured_acts_274
from app.domains.predeploy_cleanup.phase2b_routes_manifest_freeze import (
    BASELINE_EXPECTED,
    FORBIDDEN_MANIFEST_ENTITIES,
    PHASE2B_DELETE_ORDER,
    POST_EXPECTED,
    ManifestFreezeError,
    _baseline_check,
    _compute_unlock_expectations,
    _protected_closure,
    _validate_empty_groups,
    _validate_empty_routes,
    _validate_frozen_delete_order,
    _validate_iniciadores_no_surviving_refs,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    _chunk_ids,
    _fetch_ids,
    _table_for_entity,
    load_user_fk_columns,
)
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.execution_validator import validate_execution_plan
from app.domains.predeploy_cleanup.sequential_simulator import VirtualDeleteState

DELETE_COUNTS = {
    "ruta_grupo_inspector": 1706,
    "ruta_item": 854,
    "ruta_pool_dia": 353,
    "ruta_grupo": 853,
    "ruta_trabajo": 851,
    "iniciador_ruta": 369,
}

UNCHANGED_ENTITIES = (
    "actuaciones",
    "denuncia",
    "relevamiento",
    "users",
    "establecimiento_operativo",
    "orden_trabajo",
)

ORPHAN_TABLES = (
    "ruta_item",
    "ruta_pool_dia",
    "ruta_grupo",
    "ruta_grupo_inspector",
    "ruta_trabajo",
    "iniciador_ruta",
    "actuaciones",
    "denuncia",
    "relevamiento",
    "notificacion",
    "comprobacion",
    "oficio",
)

PROTECTED_ENTITIES_CHECK = (
    "actuaciones",
    "orden_trabajo",
    "inspeccion",
    "notificacion",
    "comprobacion",
    "oficio",
    "expediente",
)


def _scalar(conn: Connection, sql: str, params: dict | None = None) -> Any:
    row = conn.execute(text(sql), params or {}).fetchone()
    return row[0] if row else None


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


def load_entity_sets(execution_manifest: dict[str, Any]) -> dict[str, set[int]]:
    """Extrae IDs del manifest congelado."""
    sets: dict[str, set[int]] = {}
    for entity in PHASE2B_DELETE_ORDER:
        ids = entity_ids(execution_manifest, entity)
        expected = DELETE_COUNTS[entity]
        if len(ids) != expected:
            raise ApplyAbortError(f"{entity}: manifest has {len(ids)} ids, expected {expected}")
        if len(ids) != len(set(ids)):
            raise ApplyAbortError(f"{entity}: duplicate ids in manifest")
        sets[entity] = ids
    return sets


def load_test_document_ids(
    conn: Connection,
    protected_manifest: dict[str, Any],
    structured_acts_path: Path,
) -> dict[str, set[int]]:
    """Baseline IDs de documentos test que NO deben borrarse en 2B."""
    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    act_ids = _blocked_act_ids(conn, prot) | load_structured_acts_274(structured_acts_path)
    den_ids = _fetch_ids(
        conn,
        f"""
        SELECT d.id FROM denuncia d
        JOIN users u ON u.id = d.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )
    rel_ids = _fetch_ids(
        conn,
        f"""
        SELECT r.id FROM relevamiento r
        JOIN users u ON u.id = r.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """
    ) | RELEVAMIENTOS_QA_IDS
    return {
        "actuaciones_test": act_ids,
        "denuncias_test": den_ids,
        "relevamientos_test": rel_ids,
    }


def preflight_phase2b_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    structured_acts_path: Path,
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_prot_hash: str,
    expected_source_hashes: dict[str, str],
    backup_confirmed: bool = False,
) -> dict[str, Any]:
    """Preflight FASE 2B antes de BEGIN."""
    errors: list[str] = []

    if not backup_confirmed:
        errors.append("backup_confirmed required")

    manifest_for_hash = {
        k: v for k, v in execution_manifest.items() if not k.startswith("_")
    }
    computed = manifest_sha256(manifest_for_hash)
    if computed != expected_exec_hash:
        errors.append(f"execution hash {computed} != {expected_exec_hash}")

    manifest_sources = execution_manifest.get("source_report_hashes", {})
    for key, expected in expected_source_hashes.items():
        if manifest_sources.get(key) != expected:
            errors.append(f"source hash {key} mismatch")

    if execution_manifest.get("protected_manifest_hash") != expected_prot_hash:
        errors.append("protected_manifest_hash mismatch")

    if execution_manifest.get("writes_executed"):
        errors.append("manifest already marked writes_executed")

    baseline: dict[str, Any] = {}
    try:
        baseline = _baseline_check(conn)
    except ManifestFreezeError as exc:
        errors.append(str(exc))

    if baseline and baseline.get("database") != confirm_database:
        errors.append(f"database {baseline.get('database')}")

    entity_sets = load_entity_sets(execution_manifest)

    for entity, ids in entity_sets.items():
        missing = validate_ids_exist(conn, entity, ids, label=entity)
        if missing:
            errors.append(f"missing {entity}: {missing[:3]}")

    for forbidden in FORBIDDEN_MANIFEST_ENTITIES:
        if entity_ids(execution_manifest, forbidden):
            errors.append(f"forbidden entity in manifest: {forbidden}")

    safe_items = entity_sets["ruta_item"]
    safe_pool = entity_sets["ruta_pool_dia"]
    safe_groups = entity_sets["ruta_grupo"]
    safe_rutas = entity_sets["ruta_trabajo"]
    safe_ini = entity_sets["iniciador_ruta"]

    try:
        _validate_empty_groups(conn, safe_items, safe_groups)
        _validate_empty_routes(conn, safe_items, safe_rutas)
        _validate_iniciadores_no_surviving_refs(conn, safe_ini, safe_items, safe_pool)
    except ManifestFreezeError as exc:
        errors.append(str(exc))

    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    edges = load_fk_edges(conn)

    order_check = _validate_frozen_delete_order(PHASE2B_DELETE_ORDER, edges)
    if not order_check["valid"]:
        errors.append(f"delete order FK: {order_check['violations'][:3]}")

    virtual = VirtualDeleteState()
    for entity in PHASE2B_DELETE_ORDER:
        virtual.add_explicit(_table_for_entity(entity), entity_sets[entity])
    exec_validation = validate_execution_plan(
        conn, entity_sets, virtual, edges
    )
    if not exec_validation.get("valid"):
        errors.append(f"execution plan: {exec_validation.get('blocked_by_surviving_fk')}")

    protected_closure: dict[str, Any] = {"valid": False}
    try:
        protected_closure = _protected_closure(conn, entity_sets, prot, edges)
        if not protected_closure["valid"]:
            errors.append(
                f"protected closure: {protected_closure['full_protected_intersection']['conflicts']}"
            )
    except Exception as exc:
        errors.append(f"protected closure error: {exc}")

    engine_audit = audit_table_engines(conn, tuple(PHASE2B_DELETE_ORDER))
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
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "baseline_counts": baseline["counts"],
        "entity_counts": {k: len(v) for k, v in entity_sets.items()},
        "protected_closure": protected_closure,
        "delete_order_validated": order_check,
        "execution_validation": exec_validation,
        "engine_audit": engine_audit,
        "test_documents": {
            k: len(v)
            for k, v in load_test_document_ids(
                conn, protected_manifest, structured_acts_path
            ).items()
        },
    }


def apply_phase2b_routes_cleanup(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    structured_acts_path: Path,
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_prot_hash: str,
    expected_source_hashes: dict[str, str],
    backup_path: str,
    backup_hash: str,
    backup_size: int,
    restore_verified: bool,
) -> dict[str, Any]:
    """
    Aplica DELETE FASE 2B en transacción única.

    Raises ApplyAbortError → caller debe ROLLBACK.
    """
    entity_sets = load_entity_sets(execution_manifest)
    test_docs = load_test_document_ids(conn, protected_manifest, structured_acts_path)
    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))

    counts_before = {t: _count(conn, t) for t in BASELINE_EXPECTED}

    preflight = preflight_phase2b_apply(
        conn,
        execution_manifest,
        protected_manifest,
        structured_acts_path,
        confirm_database=confirm_database,
        expected_exec_hash=expected_exec_hash,
        expected_prot_hash=expected_prot_hash,
        expected_source_hashes=expected_source_hashes,
        backup_confirmed=True,
    )

    if not restore_verified:
        raise ApplyAbortError("restore_verified required")

    if conn.in_transaction():
        conn.rollback()

    cascade_observed: dict[str, int] = {}
    explicit_deleted: dict[str, int] = {}
    trans = conn.begin()
    try:
        for entity in PHASE2B_DELETE_ORDER:
            table = entity
            ids = entity_sets[entity]
            expected = DELETE_COUNTS[entity]
            count_before_step = _count(conn, table)

            deleted = 0
            for chunk in _chunk_ids(ids, 400):
                ph = ",".join(str(i) for i in chunk)
                result = conn.execute(text(f"DELETE FROM `{table}` WHERE id IN ({ph})"))
                deleted += result.rowcount or 0

            if deleted != expected:
                raise ApplyAbortError(f"{entity}: deleted {deleted} != {expected}")

            remain = _count_ids_exist(conn, table, ids)
            if remain:
                raise ApplyAbortError(f"{entity}: manifest ids remaining {remain}")

            count_after_step = _count(conn, table)
            cascade_observed[entity] = count_before_step - count_after_step - deleted
            explicit_deleted[entity] = deleted

        for entity in PHASE2B_DELETE_ORDER:
            actual = _count(conn, entity)
            if actual != POST_EXPECTED[entity]:
                raise ApplyAbortError(f"postcount {entity}: {actual} != {POST_EXPECTED[entity]}")

        for entity in UNCHANGED_ENTITIES:
            actual = _count(conn, entity)
            if actual != BASELINE_EXPECTED[entity]:
                raise ApplyAbortError(f"unchanged {entity}: {actual} != {BASELINE_EXPECTED[entity]}")

        manifest_remaining = {
            entity: _count_ids_exist(conn, entity, entity_sets[entity])
            for entity in PHASE2B_DELETE_ORDER
        }
        if any(manifest_remaining.values()):
            raise ApplyAbortError(f"manifest ids remaining: {manifest_remaining}")

        protected_preserved = _assert_protected_preserved(conn, protected_manifest)
        documents_preserved = _assert_documents_preserved(conn, test_docs)

        orphans = check_fk_orphans(conn, ORPHAN_TABLES)
        if orphans:
            raise ApplyAbortError(f"FK orphans: {orphans[:5]}")

        unlock_pre_commit = _compute_unlock_post_apply(conn, prot, structured_acts_path)
        users_analysis = post_commit_user_analysis(conn)

        trans.commit()
        committed = True
        status = "COMMITTED"
    except Exception as exc:
        trans.rollback()
        committed = False
        status = "ROLLED_BACK"
        raise ApplyAbortError(str(exc)) from exc

    counts_after = {t: _count(conn, t) for t in BASELINE_EXPECTED}

    return {
        "ticket": "PREDEPLOY-CLEANUP.3D",
        "applied_at": datetime.now().isoformat(),
        "database": confirm_database,
        "alembic_revision": preflight["alembic_revision"],
        "freeze_method": "backend_development_stopped_during_backup_preflight_transaction",
        "execution_manifest_path": str(execution_manifest.get("_source_path", "")),
        "execution_manifest_sha256": expected_exec_hash,
        "source_report_hashes": execution_manifest.get("source_report_hashes", {}),
        "protected_manifest_hash": expected_prot_hash,
        "backup": {
            "path": backup_path,
            "size": backup_size,
            "sha256": backup_hash,
            "restore_verified": restore_verified,
        },
        "counts_before": counts_before,
        "explicit_deleted": explicit_deleted,
        "cascade_observed": cascade_observed,
        "counts_after": counts_after,
        "manifest_ids_remaining": manifest_remaining,
        "protected_preserved": protected_preserved,
        "documents_preserved": documents_preserved,
        "orphan_checks": orphans,
        "unlock": unlock_pre_commit,
        "users": users_analysis,
        "preflight": preflight,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "phase2c_executed": False,
    }


def _compute_unlock_post_apply(
    conn: Connection,
    prot: dict[str, set[int]],
    structured_acts_path: Path,
) -> dict[str, Any]:
    """Recalcula unlock tras deletes aplicados (solo refs sobrevivientes en DB)."""
    return _compute_unlock_expectations(
        conn, set(), set(), set(), prot, structured_acts_path
    )


def _assert_protected_preserved(
    conn: Connection,
    protected_manifest: dict[str, Any],
) -> dict[str, dict[str, int]]:
    protected = load_protected_sets(protected_manifest)
    result: dict[str, dict[str, int]] = {}
    for entity in PROTECTED_ENTITIES_CHECK:
        ids = protected.get(entity, set())
        if not ids:
            result[entity] = {"expected": 0, "found": 0}
            continue
        table = _table_for_entity(entity)
        found = _count_ids_exist(conn, table, ids)
        result[entity] = {"expected": len(ids), "found": found}
        if found != len(ids):
            raise ApplyAbortError(f"protected {entity}: expected {len(ids)}, found {found}")
    return result


def _assert_documents_preserved(
    conn: Connection,
    test_docs: dict[str, set[int]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    table_map = {
        "actuaciones_test": "actuaciones",
        "denuncias_test": "denuncia",
        "relevamientos_test": "relevamiento",
    }
    for key, table in table_map.items():
        ids = test_docs[key]
        found = _count_ids_exist(conn, table, ids)
        result[key] = {"expected": len(ids), "found": found, "deleted": 0}
        if found != len(ids):
            raise ApplyAbortError(f"{key}: expected {len(ids)}, found {found}")

    qa_present = {}
    for qa_id in RELEVAMIENTOS_QA_IDS:
        exists = _scalar(conn, "SELECT COUNT(*) FROM relevamiento WHERE id = :id", {"id": qa_id})
        qa_present[qa_id] = bool(exists)
        if not exists:
            raise ApplyAbortError(f"QA relevamiento missing: {qa_id}")
    result["qa_relevamientos_present"] = qa_present
    return result


def post_commit_user_analysis(conn: Connection) -> dict[str, Any]:
    """Recalcula users test FK-free tras FASE 2B."""
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
        "users_test_fk_free": len(unlocked),
        "users_test_still_blocked": len(still_blocked),
        "unlocked_sample": sorted(unlocked)[:40],
        "blocked_sample": sorted(still_blocked)[:20],
    }
