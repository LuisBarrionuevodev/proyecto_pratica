"""Aplicación FASE 2C.1: DELETE actuaciones + denuncias + OT test (transacción única)."""

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
from app.domains.predeploy_cleanup.constants import RELEVAMIENTOS_QA_IDS
from app.domains.predeploy_cleanup.manifest_io import (
    entity_ids,
    load_manifest,
    manifest_sha256,
)
from app.domains.predeploy_cleanup.phase2c1_sources_manifest_freeze import (
    CASCADE_TABLES,
    EXPECTED_CASCADE_COUNTS,
    PHASE2C1_DELETE_ORDER,
    POST_EXPECTED,
    PROTECTED_POSTCONDITION_MIN,
    _baseline_check,
    _collect_and_freeze_cascades,
    _protected_child_intersection,
    _protected_closure,
    _validate_act_family,
    _validate_act_routing_blockers,
    _validate_den_routing_blockers,
    _validate_excluded_sets,
    _validate_ids_exist_all,
    _validate_ot_exclusive,
)
from app.domains.predeploy_cleanup.phase2c1_unlocked_sources_diag import BASELINE_POST_2B
from app.domains.predeploy_cleanup.phase2_blockers_diag import _blocked_act_ids
from app.domains.predeploy_cleanup.phase2b_routes_initiators_diag import load_structured_acts_274
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    _chunk_ids,
    _fetch_ids,
    _table_for_entity,
    load_user_fk_columns,
)
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges

CHILD_BASELINE = {
    "inspeccion": 1132,
    "actuaciones_inspector": 4427,
    "clausura": 73,
    "decomiso": 29,
    "acta_inspeccion_item": 52,
}

CHILD_POST = {
    "inspeccion": 915,
    "clausura": 69,
    "decomiso": 25,
    "acta_inspeccion_item": 52,
}

ROUTE_UNCHANGED = {
    "ruta_trabajo": 2715,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3697,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8194,
}

ORPHAN_TABLES = (
    "actuaciones",
    "inspeccion",
    "actuaciones_inspector",
    "clausura",
    "decomiso",
    "orden_trabajo",
    "denuncia",
    "iniciador_ruta",
    "notificacion",
    "comprobacion",
)


def _scalar(conn: Connection, sql: str, params: dict | None = None) -> Any:
    row = conn.execute(text(sql), params or {}).fetchone()
    return row[0] if row else None


def _count(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _count_actuaciones_inspector_rows(conn: Connection, act_ids: set[int]) -> int:
    """Filas físicas en actuaciones_inspector ligadas a actuaciones (no distinct actuaciones_id)."""
    if not act_ids:
        return 0
    total = 0
    for chunk in _chunk_ids(act_ids, 400):
        ph = ",".join(str(i) for i in chunk)
        total += int(
            _scalar(
                conn,
                f"SELECT COUNT(*) FROM actuaciones_inspector WHERE actuaciones_id IN ({ph})",
            )
            or 0
        )
    return total


def _expected_cascade_counts_for_apply(conn: Connection, act_ids: set[int]) -> dict[str, int]:
    """Cuentas CASCADE físicas; actuaciones_inspector usa filas, no distinct actuaciones_id."""
    counts = dict(EXPECTED_CASCADE_COUNTS)
    counts["actuaciones_inspector"] = _count_actuaciones_inspector_rows(conn, act_ids)
    return counts


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


def load_entity_sets(execution_manifest: dict[str, Any]) -> dict[str, set[int]]:
    sets: dict[str, set[int]] = {}
    for entity in PHASE2C1_DELETE_ORDER:
        ids = entity_ids(execution_manifest, entity)
        if entity == "actuaciones" and len(ids) != 265:
            raise ApplyAbortError(f"actuaciones count {len(ids)} != 265")
        if entity == "denuncia" and len(ids) != 75:
            raise ApplyAbortError(f"denuncia count {len(ids)} != 75")
        if entity == "orden_trabajo" and len(ids) != 265:
            raise ApplyAbortError(f"orden_trabajo count {len(ids)} != 265")
        sets[entity] = ids
    return sets


def load_cascade_ids_from_manifest(execution_manifest: dict[str, Any]) -> dict[str, set[int]]:
    cascades = execution_manifest.get("expected_cascades", {})
    result: dict[str, set[int]] = {}
    for tbl in CASCADE_TABLES:
        entry = cascades.get(tbl, {})
        result[tbl] = {int(x) for x in entry.get("ids", [])}
    return result


def load_preserved_docs(execution_manifest: dict[str, Any]) -> dict[str, set[int]]:
    refs = execution_manifest.get("preserve_document_refs", {})
    return {
        "notificacion": {int(x) for x in refs.get("notificacion", [])},
        "comprobacion": {int(x) for x in refs.get("comprobacion", [])},
    }


def preflight_phase2c1_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    structured_acts_path: Path,
    diag_path: Path,
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_diag_hash: str,
    expected_prot_hash: str,
    backup_confirmed: bool = False,
) -> dict[str, Any]:
    """Preflight FASE 2C.1 antes de BEGIN."""
    errors: list[str] = []

    if not backup_confirmed:
        errors.append("backup_confirmed required")

    manifest_for_hash = {k: v for k, v in execution_manifest.items() if not k.startswith("_")}
    computed = manifest_sha256(manifest_for_hash)
    if computed != expected_exec_hash:
        errors.append(f"execution hash {computed} != {expected_exec_hash}")

    if execution_manifest.get("source_diag_sha256") != expected_diag_hash:
        errors.append("source_diag_sha256 mismatch")
    if execution_manifest.get("protected_manifest_sha256") != expected_prot_hash:
        errors.append("protected_manifest_sha256 mismatch")

    try:
        baseline = _baseline_check(conn)
        for tbl, expected in CHILD_BASELINE.items():
            actual = _count(conn, tbl)
            if actual != expected:
                errors.append(f"child baseline {tbl}: {actual} != {expected}")
    except Exception as exc:
        errors.append(str(exc))

    entity_sets = load_entity_sets(execution_manifest)
    preserved = load_preserved_docs(execution_manifest)
    cascade_report: dict[str, Any] = {}
    excluded: dict[str, Any] = {}
    closure: dict[str, Any] = {}

    try:
        _validate_ids_exist_all(conn, entity_sets)
    except Exception as exc:
        errors.append(str(exc))

    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    edges = load_fk_edges(conn)

    try:
        _validate_act_family(conn, entity_sets["actuaciones"], structured_acts_path, prot)
        _validate_act_routing_blockers(conn, entity_sets["actuaciones"])
        _validate_den_routing_blockers(conn, entity_sets["denuncia"])
        cascade_report = _collect_and_freeze_cascades(conn, entity_sets["actuaciones"], edges)
        cascade_ids = {k: set(v) for k, v in cascade_report["cascade_ids"].items()}
        ai_rows = _count_actuaciones_inspector_rows(conn, entity_sets["actuaciones"])
        cascade_report["actuaciones_inspector_row_count"] = ai_rows
        cascade_report["actuaciones_inspector_manifest_distinct_act_ids"] = len(
            cascade_ids.get("actuaciones_inspector", set())
        )
        child_prot = _protected_child_intersection(cascade_ids, prot)
        if not child_prot["valid"]:
            errors.append(f"protected children: {child_prot['conflicts']}")

        set_act_old = _blocked_act_ids(conn, prot)
        set_act_structured = load_structured_acts_274(structured_acts_path)
        union_413 = set_act_old | set_act_structured
        blocked_acts = {a for a in union_413 if a not in entity_sets["actuaciones"]}
        for aid in union_413 - entity_sets["actuaciones"]:
            ini = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}")
            ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}")
            rp = _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE actuacion_id = {aid}")
            if ini or ri or rp:
                blocked_acts.add(aid)

        _validate_ot_exclusive(
            conn,
            entity_sets["actuaciones"],
            entity_sets["orden_trabajo"],
            prot,
            blocked_acts,
        )
        excluded = _validate_excluded_sets(conn, entity_sets, diag_path)
        closure = _protected_closure(entity_sets, cascade_ids, prot)
        if not closure["valid"]:
            errors.append("protected closure failed")

        for tbl in ("notificacion", "comprobacion"):
            found = _count_ids_exist(conn, tbl, preserved[tbl])
            if found != len(preserved[tbl]):
                errors.append(f"preserved {tbl}: {found} != {len(preserved[tbl])}")

        if len(preserved["notificacion"]) != 199 or len(preserved["comprobacion"]) != 20:
            errors.append("preserved doc count mismatch")

    except Exception as exc:
        errors.append(str(exc))

    engine_audit = audit_table_engines(conn, tuple(PHASE2C1_DELETE_ORDER))
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
        "cascade_report": cascade_report,
        "excluded": excluded,
        "protected_closure": closure,
        "preserved_docs": {k: len(v) for k, v in preserved.items()},
    }


def apply_phase2c1_sources_cleanup(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    structured_acts_path: Path,
    diag_path: Path,
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_diag_hash: str,
    expected_prot_hash: str,
    backup_path: str,
    backup_hash: str,
    backup_size: int,
    restore_verified: bool,
) -> dict[str, Any]:
    """Aplica DELETE FASE 2C.1 en transacción única."""
    entity_sets = load_entity_sets(execution_manifest)
    cascade_ids_frozen = load_cascade_ids_from_manifest(execution_manifest)
    preserved_docs = load_preserved_docs(execution_manifest)
    excluded_blocked = set(execution_manifest.get("excluded", {}).get("blocked_acts_148", []))
    excluded_rel = set(execution_manifest.get("excluded", {}).get("relevamientos_26", []))

    counts_before = {**BASELINE_POST_2B, **CHILD_BASELINE}
    for t in BASELINE_POST_2B:
        counts_before[t] = _count(conn, t)
    for t in CHILD_BASELINE:
        counts_before[t] = _count(conn, t)

    preflight = preflight_phase2c1_apply(
        conn,
        execution_manifest,
        protected_manifest,
        structured_acts_path,
        diag_path,
        confirm_database=confirm_database,
        expected_exec_hash=expected_exec_hash,
        expected_diag_hash=expected_diag_hash,
        expected_prot_hash=expected_prot_hash,
        backup_confirmed=True,
    )

    if not restore_verified:
        raise ApplyAbortError("restore_verified required")

    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    den_domicilio_ids: set[int] = set()
    for did in entity_sets["denuncia"]:
        row = conn.execute(
            text("SELECT domicilio_id FROM denuncia WHERE id = :id"), {"id": did}
        ).fetchone()
        if row and row[0]:
            den_domicilio_ids.add(row[0])

    if conn.in_transaction():
        conn.rollback()

    cascade_deleted: dict[str, int] = {}
    explicit_deleted: dict[str, int] = {}
    act_ids = entity_sets["actuaciones"]
    expected_cascades = _expected_cascade_counts_for_apply(conn, act_ids)
    child_post = {
        **CHILD_POST,
        "actuaciones_inspector": CHILD_BASELINE["actuaciones_inspector"]
        - expected_cascades["actuaciones_inspector"],
    }
    if conn.in_transaction():
        conn.commit()
    trans = conn.begin()
    try:
        child_counts_before = {t: _count(conn, t) for t in CHILD_BASELINE}

        explicit_deleted["actuaciones"] = _delete_ids(conn, "actuaciones", act_ids)
        if explicit_deleted["actuaciones"] != 265:
            raise ApplyAbortError(f"act deleted {explicit_deleted['actuaciones']} != 265")

        remain_acts = _count_ids_exist(conn, "actuaciones", act_ids)
        if remain_acts:
            raise ApplyAbortError(f"act remaining {remain_acts}")

        for tbl in ("inspeccion", "actuaciones_inspector", "clausura", "decomiso"):
            frozen_ids = cascade_ids_frozen.get(tbl, set())
            if frozen_ids and tbl != "actuaciones_inspector":
                remain = _count_ids_exist(conn, tbl, frozen_ids)
                if remain:
                    raise ApplyAbortError(f"cascade {tbl} ids remain: {remain}")
            elif frozen_ids and tbl == "actuaciones_inspector":
                ph = ",".join(str(i) for i in sorted(frozen_ids))
                remain = int(
                    _scalar(
                        conn,
                        f"SELECT COUNT(*) FROM actuaciones_inspector "
                        f"WHERE actuaciones_id IN ({ph})",
                    )
                    or 0
                )
                if remain:
                    raise ApplyAbortError(f"cascade actuaciones_inspector rows remain: {remain}")
            after = _count(conn, tbl)
            deleted_n = child_counts_before[tbl] - after
            expected = expected_cascades[tbl]
            if deleted_n != expected:
                raise ApplyAbortError(f"cascade {tbl}: deleted {deleted_n} != {expected}")
            if after != child_post[tbl]:
                raise ApplyAbortError(f"cascade post {tbl}: {after} != {child_post[tbl]}")
            cascade_deleted[tbl] = deleted_n

        if _count(conn, "acta_inspeccion_item") != CHILD_POST["acta_inspeccion_item"]:
            raise ApplyAbortError("acta_inspeccion_item count changed unexpectedly")

        for tbl, ids in preserved_docs.items():
            found = _count_ids_exist(conn, tbl, ids)
            if found != len(ids):
                raise ApplyAbortError(f"preserved {tbl}: {found}/{len(ids)}")

        for ot_id in entity_sets["orden_trabajo"]:
            refs = _fetch_ids(
                conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}"
            )
            if refs:
                raise ApplyAbortError(f"OT {ot_id} still has acts: {refs[:5]}")

        explicit_deleted["denuncia"] = _delete_ids(conn, "denuncia", entity_sets["denuncia"])
        if explicit_deleted["denuncia"] != 75:
            raise ApplyAbortError(f"den deleted {explicit_deleted['denuncia']} != 75")

        for dom_id in den_domicilio_ids:
            exists = _scalar(conn, "SELECT COUNT(*) FROM domicilio WHERE id = :id", {"id": dom_id})
            if not exists:
                raise ApplyAbortError(f"domicilio missing {dom_id}")

        explicit_deleted["orden_trabajo"] = _delete_ids(
            conn, "orden_trabajo", entity_sets["orden_trabajo"]
        )
        if explicit_deleted["orden_trabajo"] != 265:
            raise ApplyAbortError(f"ot deleted {explicit_deleted['orden_trabajo']} != 265")

        for entity in PHASE2C1_DELETE_ORDER:
            if _count_ids_exist(conn, entity, entity_sets[entity]):
                raise ApplyAbortError(f"manifest ids remain: {entity}")

        for entity, expected in POST_EXPECTED.items():
            if _count(conn, entity) != expected:
                raise ApplyAbortError(f"post {entity}: {_count(conn, entity)} != {expected}")

        for tbl, expected in child_post.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"post child {tbl}: {_count(conn, tbl)} != {expected}")

        for tbl, expected in ROUTE_UNCHANGED.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"route changed {tbl}")

        if _count(conn, "users") != 2803:
            raise ApplyAbortError("users count changed")
        if _count(conn, "establecimiento_operativo") != 1657:
            raise ApplyAbortError("eo count changed")
        if _count(conn, "relevamiento") != 4592:
            raise ApplyAbortError("relevamiento count changed")
        if _count(conn, "domicilio") < len(den_domicilio_ids):
            raise ApplyAbortError("domicilio delete detected")

        blocked_present = _count_ids_exist(conn, "actuaciones", excluded_blocked)
        if blocked_present != len(excluded_blocked):
            raise ApplyAbortError(f"blocked acts: {blocked_present}/{len(excluded_blocked)}")

        rel_set = excluded_rel or RELEVAMIENTOS_QA_IDS
        rel_present = _count_ids_exist(conn, "relevamiento", rel_set)
        if rel_present != len(rel_set):
            raise ApplyAbortError(f"relevamientos: {rel_present}/{len(rel_set)}")

        protected_preserved = {}
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

    counts_after = {t: _count(conn, t) for t in BASELINE_POST_2B}
    for t in CHILD_BASELINE:
        counts_after[t] = _count(conn, t)

    users_unlock = post_commit_user_analysis(conn)

    return {
        "ticket": "PREDEPLOY-CLEANUP.3E.2",
        "applied_at": datetime.now().isoformat(),
        "database": confirm_database,
        "alembic_revision": preflight["baseline"]["alembic_revision"],
        "freeze_method": "backend_development_stopped_during_backup_preflight_transaction",
        "execution_manifest_path": str(execution_manifest.get("_source_path", "")),
        "execution_manifest_sha256": expected_exec_hash,
        "source_diag_sha256": expected_diag_hash,
        "protected_manifest_sha256": expected_prot_hash,
        "backup": {
            "path": backup_path,
            "size": backup_size,
            "sha256": backup_hash,
            "restore_verified": restore_verified,
        },
        "counts_before": counts_before,
        "explicit_deleted": explicit_deleted,
        "cascade_deleted": cascade_deleted,
        "cascade_expected_physical": expected_cascades,
        "cascade_manifest_distinct_actuaciones_inspector": len(
            cascade_ids_frozen.get("actuaciones_inspector", set())
        ),
        "preserved_document_refs": {
            k: sorted(v) for k, v in preserved_docs.items()
        },
        "excluded_preserved": {
            "blocked_acts_148_count": len(excluded_blocked),
            "relevamientos_26_count": len(excluded_rel),
        },
        "counts_after": counts_after,
        "manifest_ids_remaining": {e: 0 for e in PHASE2C1_DELETE_ORDER},
        "protected_preserved": protected_preserved,
        "orphan_checks": orphans,
        "users_unlock": users_unlock,
        "preflight": preflight,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "phase2c2_executed": False,
    }


def post_commit_user_analysis(conn: Connection) -> dict[str, Any]:
    """Recalcula users test FK-free tras FASE 2C.1."""
    from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE

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
        "users_test_fk_free_after_2c1": len(unlocked),
        "users_test_still_blocked": len(still_blocked),
        "unlocked_sample": sorted(unlocked)[:40],
    }
