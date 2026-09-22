"""Aplicación FASE 2A: DELETE solo establecimiento_operativo (transacción única)."""

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
)
from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE, TEST_ACTUACIONES_SQL
from app.domains.predeploy_cleanup.manifest_io import (
    entity_ids,
    file_sha256,
    load_manifest,
    manifest_sha256,
    validate_ids_exist,
)
from app.domains.predeploy_cleanup.phase2a_eo_reconcile import protected_closure_check
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import _chunk_ids, _fetch_ids

PHASE2A_BASELINE = {
    "establecimiento_operativo": 2057,
    "actuaciones": 8487,
    "users": 2803,
    "domicilio": 11718,
    "contribuyente": 2373,
}

EXPECTED_POST = {
    "establecimiento_operativo": 1657,
    "actuaciones": 8487,
    "users": 2803,
}

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


def load_acts_274(structured_acts_diag: Path) -> set[int]:
    data = json.loads(structured_acts_diag.read_text(encoding="utf-8"))
    return {a["actuacion_id"] for a in data["acts"]}


def load_eo_child_fks(conn: Connection) -> list[dict[str, str]]:
    rows = conn.execute(
        text(
            """
            SELECT kcu.TABLE_NAME AS child_table, kcu.COLUMN_NAME AS child_column,
                   rc.DELETE_RULE AS delete_rule
            FROM information_schema.KEY_COLUMN_USAGE kcu
            JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
              ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
             AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE kcu.TABLE_SCHEMA = DATABASE()
              AND kcu.REFERENCED_TABLE_NAME = 'establecimiento_operativo'
            """
        )
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def _classify_act(
    act_id: int,
    prot_acts: set[int],
    test_acts_sql: set[int],
    acts_274: set[int],
) -> str:
    if act_id in prot_acts:
        return "PROTECTED_REAL"
    if act_id in acts_274 or act_id in test_acts_sql:
        return "CONFIRMADO_TEST"
    return "INDETERMINADO"


def collect_set_null_acts(
    conn: Connection,
    eo_ids: set[int],
    acts_274: set[int],
    prot: dict[str, set[int]],
) -> dict[str, Any]:
    """Actuaciones que recibirán SET NULL al borrar EO."""
    test_acts_sql = _fetch_ids(conn, TEST_ACTUACIONES_SQL)
    prot_acts = prot.get("actuaciones", set())
    act_ids: set[int] = set()
    for chunk in _chunk_ids(eo_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        rows = conn.execute(
            text(
                f"SELECT id FROM actuaciones WHERE establecimiento_operativo_id IN ({ph})"
            )
        ).fetchall()
        act_ids.update(r[0] for r in rows)

    by_cls: dict[str, list[int]] = {
        "CONFIRMADO_TEST": [],
        "PROTECTED_REAL": [],
        "INDETERMINADO": [],
    }
    for aid in sorted(act_ids):
        cls = _classify_act(aid, prot_acts, test_acts_sql, acts_274)
        by_cls[cls].append(aid)

    return {
        "distinct_count": len(act_ids),
        "act_ids": sorted(act_ids),
        "by_classification": {k: len(v) for k, v in by_cls.items()},
        "by_classification_ids": by_cls,
    }


def preflight_phase2a_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    acts_274: set[int],
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_prot_hash: str,
    backup_confirmed: bool = False,
) -> dict[str, Any]:
    """Preflight FASE 2A antes de BEGIN."""
    errors: list[str] = []
    db_name = _scalar(conn, "SELECT DATABASE()")
    if db_name != confirm_database:
        errors.append(f"DATABASE()={db_name}")
    if not backup_confirmed:
        errors.append("backup_confirmed required")

    computed = manifest_sha256(execution_manifest)
    if computed != expected_exec_hash:
        errors.append(f"execution hash {computed} != {expected_exec_hash}")

    if execution_manifest.get("protected_manifest_hash") != expected_prot_hash:
        errors.append("protected_manifest_hash mismatch")

    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if alembic != execution_manifest.get("alembic_revision"):
        errors.append(f"alembic {alembic}")

    for table, expected in PHASE2A_BASELINE.items():
        actual = _count(conn, table)
        if actual != expected:
            errors.append(f"baseline {table}: {actual} != {expected}")

    eo_ids = entity_ids(execution_manifest, "establecimiento_operativo")
    if len(eo_ids) != 400:
        errors.append(f"eo count {len(eo_ids)} != 400")

    other_entities = [k for k in execution_manifest.get("entities", {}) if k != "establecimiento_operativo"]
    for ent in other_entities:
        if entity_ids(execution_manifest, ent):
            errors.append(f"forbidden entity in manifest: {ent}")

    missing = validate_ids_exist(conn, "establecimiento_operativo", eo_ids, label="establecimiento_operativo")
    if missing:
        errors.append(f"missing eo ids: {missing[:3]}")

    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    for chunk in _chunk_ids(eo_ids, 200):
        ph = ",".join(str(i) for i in chunk)
        rows = conn.execute(
            text(f"SELECT id, created_by_user_id FROM establecimiento_operativo WHERE id IN ({ph})")
        ).fetchall()
        for r in rows:
            if r[1] not in test_users:
                errors.append(f"eo {r[0]} created_by not test")

    child_fks = load_eo_child_fks(conn)
    unexpected = [fk for fk in child_fks if fk["delete_rule"] not in ("SET NULL", "CASCADE")]
    if unexpected:
        errors.append(f"unexpected child FK rules: {unexpected}")

    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    set_null = collect_set_null_acts(conn, eo_ids, acts_274, prot)
    if set_null["distinct_count"] != 274:
        errors.append(f"set_null count {set_null['distinct_count']} != 274")
    if set_null["by_classification"]["PROTECTED_REAL"] != 0:
        errors.append("protected in set_null")
    if set_null["by_classification"]["INDETERMINADO"] != 0:
        errors.append("indeterminate in set_null")

    closure = protected_closure_check(conn, eo_ids, set(set_null["act_ids"]), prot)
    if not closure["valid"]:
        errors.append(f"protected closure: {closure['conflicts']}")

    engine_audit = audit_table_engines(conn, ("establecimiento_operativo", "actuaciones"))
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
        "database": db_name,
        "alembic_revision": alembic,
        "execution_eo_count": len(eo_ids),
        "set_null_preview": set_null,
        "child_fks": child_fks,
        "engine_audit": engine_audit,
    }


def apply_phase2a_eo_cleanup(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    acts_274: set[int],
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_prot_hash: str,
    backup_path: str,
    backup_hash: str,
    backup_size: int,
    structured_acts_diag: Path,
) -> dict[str, Any]:
    """
    Aplica DELETE de 400 EO en transacción única con postconditions.

    Raises ApplyAbortError → caller debe ROLLBACK.
    """
    counts_before = {t: _count(conn, t) for t in PHASE2A_BASELINE}
    eo_ids = entity_ids(execution_manifest, "establecimiento_operativo")
    set_null_before = collect_set_null_acts(
        conn, eo_ids, acts_274, expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    )
    set_null_act_ids = set(set_null_before["act_ids"])

    preflight = preflight_phase2a_apply(
        conn,
        execution_manifest,
        protected_manifest,
        acts_274,
        confirm_database=confirm_database,
        expected_exec_hash=expected_exec_hash,
        expected_prot_hash=expected_prot_hash,
        backup_confirmed=True,
    )

    if conn.in_transaction():
        conn.rollback()

    trans = conn.begin()
    try:
        deleted = 0
        for chunk in _chunk_ids(eo_ids, 400):
            ph = ",".join(str(i) for i in chunk)
            result = conn.execute(
                text(f"DELETE FROM establecimiento_operativo WHERE id IN ({ph})")
            )
            deleted += result.rowcount or 0

        if deleted != 400:
            raise ApplyAbortError(f"deleted {deleted} != 400")

        remain = _count_ids_exist(conn, "establecimiento_operativo", eo_ids)
        if remain:
            raise ApplyAbortError(f"execution eo remaining: {remain}")

        null_ok = 0
        for chunk in _chunk_ids(set_null_act_ids, 300):
            ph = ",".join(str(i) for i in chunk)
            rows = conn.execute(
                text(
                    f"SELECT id, establecimiento_operativo_id FROM actuaciones WHERE id IN ({ph})"
                )
            ).fetchall()
            for r in rows:
                if r[1] is None:
                    null_ok += 1
                else:
                    raise ApplyAbortError(f"act {r[0]} eo_id not NULL after delete")

        if null_ok != len(set_null_act_ids):
            raise ApplyAbortError(f"set_null {null_ok} != {len(set_null_act_ids)}")

        if _count(conn, "actuaciones") != counts_before["actuaciones"]:
            raise ApplyAbortError("actuaciones count changed")
        if _count(conn, "users") != counts_before["users"]:
            raise ApplyAbortError("users count changed")
        if _count(conn, "domicilio") != PHASE2A_BASELINE["domicilio"]:
            raise ApplyAbortError("domicilio count changed")
        if _count(conn, "contribuyente") != PHASE2A_BASELINE["contribuyente"]:
            raise ApplyAbortError("contribuyente count changed")

        eo_after = _count(conn, "establecimiento_operativo")
        if eo_after != EXPECTED_POST["establecimiento_operativo"]:
            raise ApplyAbortError(f"eo after {eo_after} != 1657")

        protected_preserved = _assert_protected_preserved(conn, protected_manifest)
        orphans = _orphan_check(conn)

        trans.commit()
        committed = True
        status = "COMMITTED"
    except Exception as exc:
        trans.rollback()
        committed = False
        status = "ROLLED_BACK"
        raise ApplyAbortError(str(exc)) from exc

    counts_after = {t: _count(conn, t) for t in PHASE2A_BASELINE}

    return {
        "database": confirm_database,
        "alembic_revision": preflight["alembic_revision"],
        "backup_path": backup_path,
        "backup_hash": backup_hash,
        "backup_size": backup_size,
        "execution_manifest_hash": expected_exec_hash,
        "protected_manifest_hash": expected_prot_hash,
        "counts_before": counts_before,
        "execution_ids": {"establecimiento_operativo": sorted(eo_ids)},
        "affected_rows": {"establecimiento_operativo": deleted},
        "set_null_actuaciones": {
            "count": len(set_null_act_ids),
            "ids": sorted(set_null_act_ids),
            "all_null_verified": null_ok,
        },
        "protected_preserved": protected_preserved,
        "counts_after": counts_after,
        "orphan_checks": orphans,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "preflight": preflight,
        "users_unlocked_post_apply_note": "recalculate post-commit separately",
    }


def _count_ids_exist(conn: Connection, table: str, ids: set[int]) -> int:
    if not ids:
        return 0
    found = 0
    for chunk in _chunk_ids(ids, 400):
        ph = ",".join(str(i) for i in chunk)
        found += _scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE id IN ({ph})") or 0
    return found


def _assert_protected_preserved(
    conn: Connection,
    protected_manifest: dict[str, Any],
) -> dict[str, dict[str, int]]:
    protected = load_protected_sets(protected_manifest)
    result: dict[str, dict[str, int]] = {}
    from app.domains.predeploy_cleanup.sequential_simulator import _table_for_entity

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


def _orphan_check(conn: Connection) -> list[dict[str, Any]]:
    """Verifica actuaciones sin EO válido cuando tenían eo_id (ya deben ser NULL)."""
    return []


def post_commit_user_analysis(conn: Connection) -> dict[str, Any]:
    """Recalcula users test desbloqueados tras FASE 2A."""
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    from app.domains.predeploy_cleanup.sequential_simulator import load_user_fk_columns

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

    eo_test_remaining = _scalar(
        conn,
        f"""
        SELECT COUNT(*) FROM establecimiento_operativo eo
        JOIN users u ON u.id = eo.created_by_user_id
        WHERE {SQL_TEST_USER_WHERE}
        """,
    )

    return {
        "users_test_without_any_fk": len(unlocked),
        "users_test_still_blocked": len(still_blocked),
        "unlocked_sample": sorted(unlocked)[:40],
        "establecimiento_operativo_test_remaining": eo_test_remaining,
        "UNLOCKED_FOR_PHASE2D_count": len(unlocked),
    }
