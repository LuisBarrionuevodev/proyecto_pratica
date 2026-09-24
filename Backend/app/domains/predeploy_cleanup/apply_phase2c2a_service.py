"""Aplicación FASE 2C.2A: DELETE 155 iniciador_ruta test (transacción única)."""

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
from app.domains.predeploy_cleanup.constants import RELEVAMIENTOS_QA_IDS, SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.manifest_io import entity_ids, manifest_sha256
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar, audit_otro_relevador_qa
from app.domains.predeploy_cleanup.phase2c2_notification_source_diag import PROTECTED_COMP_CLOSURE_8
from app.domains.predeploy_cleanup.phase2c2a_initiators_manifest_freeze import (
    BASELINE_POST_2C1,
    EXPECTED_RELEVAMIENTO,
    EXPECTED_RESIDUAL,
    EXPECTED_SAFE_TOTAL,
    PHASE2C2A_DELETE_ORDER,
    POST_INICIADOR,
    _baseline_check,
    _excluded_indeterminate_initiators,
    _incoming_fk_blockers,
    _protected_comp_regression,
    _simulate_unlock,
    load_safe_initiators_from_diag,
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

EXPECTED_EXEC_HASH = "87333d638c21d9025335019122f34a0b496306e066009f89554b6d1c43e02d2a"
EXPECTED_SOURCE_DIAG_HASH = "b7e26f3e41638289daa62cef159a96ffba81f4630b0a5cc9d1a882584ecce7ab"
EXPECTED_PROT_HASH = "d8a1fda3a10e46dcdb90b22038d73e1e08c76754a59c96dc11cff4377a3b102e"

PROTECTED_POSTCONDITION_MIN = {
    "actuaciones": 1189,
    "orden_trabajo": 1176,
    "inspeccion": 170,
    "notificacion": 168,
    "comprobacion": 56,
    "oficio": 40,
    "expediente": 40,
}

UNCHANGED_TABLES = tuple(k for k in BASELINE_POST_2C1 if k != "iniciador_ruta")

ORPHAN_TABLES = (
    "iniciador_ruta",
    "notificacion",
    "relevamiento",
    "actuaciones",
    "comprobacion",
    "expediente",
    "oficio",
    "ruta_item",
    "ruta_pool_dia",
)

SOURCE_9110_ID = 9110


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


def _route_refs(conn: Connection, ini_ids: set[int]) -> dict[str, int]:
    ri = 0
    rp = 0
    for chunk in _chunk_ids(ini_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        ri += int(
            _scalar(conn, f"SELECT COUNT(*) FROM ruta_item WHERE iniciador_ruta_id IN ({ph})") or 0
        )
        rp += int(
            _scalar(conn, f"SELECT COUNT(*) FROM ruta_pool_dia WHERE iniciador_ruta_id IN ({ph})") or 0
        )
    return {"ruta_item": ri, "ruta_pool_dia": rp}


def _load_ini_sets(execution_manifest: dict[str, Any]) -> dict[str, set[int]]:
    ini_ids = entity_ids(execution_manifest, "iniciador_ruta")
    if len(ini_ids) != EXPECTED_SAFE_TOTAL:
        raise ApplyAbortError(f"iniciador_ruta count {len(ini_ids)} != {EXPECTED_SAFE_TOTAL}")
    rel_set = set(execution_manifest["breakdown"]["relevamiento_RELEVAMIENTO"])
    residual = ini_ids - rel_set
    if len(residual) != EXPECTED_RESIDUAL:
        raise ApplyAbortError(f"residual {len(residual)} != {EXPECTED_RESIDUAL}")
    if len(rel_set) != EXPECTED_RELEVAMIENTO:
        raise ApplyAbortError(f"relevamiento {len(rel_set)} != {EXPECTED_RELEVAMIENTO}")
    return {
        "iniciador_ruta": ini_ids,
        "residual": residual,
        "relevamiento": rel_set,
    }


def _snapshot_sources(
    conn: Connection,
    execution_manifest: dict[str, Any],
    residual_ids: set[int],
    rel_ids: set[int],
) -> dict[str, Any]:
    """Congela IDs source antes del DELETE."""
    notif_ids = {int(x) for x in execution_manifest["notificacion_sources_preserved"]["notificacion_ids"]}
    if len(notif_ids) != execution_manifest["notificacion_sources_preserved"]["count"]:
        raise ApplyAbortError("notificacion source count mismatch in manifest")

    row = conn.execute(
        text(
            """
            SELECT id, tipo_iniciador, notificacion_id, comprobacion_id, oficio_id,
                   relevamiento_id, actuacion_id, denuncia_id
            FROM iniciador_ruta WHERE id = :id
            """
        ),
        {"id": SOURCE_9110_ID},
    ).fetchone()
    if not row:
        raise ApplyAbortError(f"iniciador {SOURCE_9110_ID} missing for source snapshot")
    source_9110 = {
        "iniciador_id": row[0],
        "tipo_iniciador": row[1],
        "notificacion_id": row[2],
        "comprobacion_id": row[3],
        "oficio_id": row[4],
        "relevamiento_id": row[5],
        "actuacion_id": row[6],
        "denuncia_id": row[7],
    }

    rel_present = _count_ids_exist(conn, "relevamiento", rel_ids)
    if rel_present != len(rel_ids):
        raise ApplyAbortError(f"relevamientos snapshot: {rel_present}/{len(rel_ids)}")

    notif_present = _count_ids_exist(conn, "notificacion", notif_ids)
    if notif_present != len(notif_ids):
        raise ApplyAbortError(f"notificaciones snapshot: {notif_present}/{len(notif_ids)}")

    return {
        "notificaciones": sorted(notif_ids),
        "notificaciones_count": len(notif_ids),
        "source_9110": source_9110,
        "relevamientos": sorted(rel_ids),
        "relevamientos_count": len(rel_ids),
    }


def _verify_sources_preserved(conn: Connection, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Verifica IDs source tras DELETE (no solo COUNT)."""
    notif_ids = set(snapshot["notificaciones"])
    rel_ids = set(snapshot["relevamientos"])
    notif_found = _count_ids_exist(conn, "notificacion", notif_ids)
    rel_found = _count_ids_exist(conn, "relevamiento", rel_ids)

    src9110 = snapshot["source_9110"]
    preserved_9110: dict[str, Any] = {}
    fk_map = {
        "notificacion_id": "notificacion",
        "comprobacion_id": "comprobacion",
        "oficio_id": "oficio",
        "relevamiento_id": "relevamiento",
        "actuacion_id": "actuaciones",
        "denuncia_id": "denuncia",
    }
    for col, table in fk_map.items():
        val = src9110.get(col)
        if val:
            exists = bool(_scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE id = :id", {"id": val}))
            preserved_9110[col] = {"id": val, "exists": exists}
            if not exists:
                raise ApplyAbortError(f"source 9110 {col}={val} missing from {table}")

    if notif_found != len(notif_ids):
        raise ApplyAbortError(f"notificaciones preserved {notif_found}/{len(notif_ids)}")
    if rel_found != len(rel_ids):
        raise ApplyAbortError(f"relevamientos preserved {rel_found}/{len(rel_ids)}")

    return {
        "notificaciones": {"expected": len(notif_ids), "found": notif_found},
        "source_9110": preserved_9110,
        "relevamientos": {"expected": len(rel_ids), "found": rel_found},
    }


def _compute_unlock_post_delete(
    conn: Connection,
    acts_148: set[int],
    rel_26: set[int],
) -> dict[str, Any]:
    unlocked_acts: list[int] = []
    still_acts: list[int] = []
    for aid in sorted(acts_148):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}")
        ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}")
        rp = _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE actuacion_id = {aid}")
        if not inis and not ri and not rp:
            unlocked_acts.append(aid)
        else:
            still_acts.append(aid)

    unlocked_rel: list[int] = []
    still_rel: list[int] = []
    for rid in sorted(rel_26):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE relevamiento_id = {rid}")
        if not inis:
            unlocked_rel.append(rid)
        else:
            still_rel.append(rid)

    return {
        "actuaciones": {
            "unlocked": unlocked_acts,
            "blocked": still_acts,
            "unlocked_count": len(unlocked_acts),
            "blocked_count": len(still_acts),
        },
        "relevamientos": {
            "unlocked": unlocked_rel,
            "blocked": still_rel,
            "unlocked_count": len(unlocked_rel),
            "blocked_count": len(still_rel),
        },
    }


def post_commit_user_analysis(conn: Connection) -> dict[str, Any]:
    """Recalcula users test FK-free tras FASE 2C.2A."""
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    fk_columns = load_user_fk_columns(conn)
    unlocked: list[int] = []
    still_blocked: list[int] = []
    for uid in test_users:
        refs = []
        for table, col in fk_columns:
            n = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE `{col}` = :uid", {"uid": uid}) or 0)
            if n:
                refs.append(table)
        if not refs:
            unlocked.append(uid)
        else:
            still_blocked.append(uid)
    return {
        "users_test_fk_free": len(unlocked),
        "users_test_still_blocked": len(still_blocked),
        "baseline_reference": 802,
        "simulation_reference_after_2c2a": 812,
    }


def preflight_phase2c2a_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    source_diag_path: Path,
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_prot_hash: str,
    backup_confirmed: bool = False,
    restore_verified: bool = False,
) -> dict[str, Any]:
    """Preflight FASE 2C.2A antes de BEGIN."""
    errors: list[str] = []

    if not backup_confirmed:
        errors.append("backup_confirmed required")
    if not restore_verified:
        errors.append("restore_verified required")

    manifest_for_hash = {k: v for k, v in execution_manifest.items() if not k.startswith("_")}
    computed = manifest_sha256(manifest_for_hash)
    if computed != expected_exec_hash:
        errors.append(f"execution hash {computed} != {expected_exec_hash}")

    if execution_manifest.get("source_diag_sha256") != expected_source_diag_hash:
        errors.append("source_diag_sha256 mismatch")
    if execution_manifest.get("protected_manifest_sha256") != expected_prot_hash:
        errors.append("protected_manifest_sha256 mismatch")

    try:
        baseline = _baseline_check(conn)
    except Exception as exc:
        errors.append(str(exc))

    try:
        sets = _load_ini_sets(execution_manifest)
        ini_ids = sets["iniciador_ruta"]
        found = _count_ids_exist(conn, "iniciador_ruta", ini_ids)
        if found != len(ini_ids):
            errors.append(f"iniciadores exist: {found}/{len(ini_ids)}")

        route_refs = _route_refs(conn, ini_ids)
        if route_refs["ruta_item"] or route_refs["ruta_pool_dia"]:
            errors.append(f"route refs: {route_refs}")

        fk_blockers = _incoming_fk_blockers(conn, ini_ids)
        if fk_blockers:
            errors.append(f"incoming FK blockers: {fk_blockers[:3]}")

        diag_data = load_safe_initiators_from_diag(source_diag_path)
        excluded_ini = _excluded_indeterminate_initiators(diag_data["diag"])
        if ini_ids & excluded_ini:
            errors.append(f"excluded intersection: {sorted(ini_ids & excluded_ini)[:5]}")

        acts_148 = {int(x) for x in execution_manifest["excluded"]["acts_148"]}
        rel_26 = {int(x) for x in execution_manifest["excluded"]["relevamientos_26"]}
        if len(acts_148) != 148:
            errors.append(f"acts_148: {len(acts_148)}")
        if len(rel_26) != 26:
            errors.append(f"rel_26: {len(rel_26)}")

        acts_present = _count_ids_exist(conn, "actuaciones", acts_148)
        if acts_present != 148:
            errors.append(f"acts_148 present: {acts_present}")

        rel_present = _count_ids_exist(conn, "relevamiento", rel_26)
        if rel_present != 26:
            errors.append(f"rel_26 present: {rel_present}")

        for rid in RELEVAMIENTOS_QA_IDS:
            if rid not in rel_26:
                errors.append(f"QA relev {rid} missing")

        unlock_sim = _simulate_unlock(conn, acts_148, rel_26, ini_ids)
        if unlock_sim["actuaciones"]["unlocked_count"] != 110:
            errors.append(f"acts unlock sim: {unlock_sim['actuaciones']['unlocked_count']}")
        if unlock_sim["actuaciones"]["blocked_count"] != 38:
            errors.append(f"acts blocked sim: {unlock_sim['actuaciones']['blocked_count']}")
        if unlock_sim["relevamientos"]["unlocked_count"] != 26:
            errors.append(f"rel unlock sim: {unlock_sim['relevamientos']['unlocked_count']}")

        prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
        virtual = VirtualDeleteState()
        virtual.add_explicit("iniciador_ruta", ini_ids)
        closure = protection_closure_check(virtual, prot)
        if not closure.get("valid"):
            errors.append(f"protected closure: {closure.get('conflicts', [])[:3]}")

        comp_reg = _protected_comp_regression(conn, prot)
        if not comp_reg.get("all_protected"):
            errors.append("protected comprobacion regression failed")

        sources_snapshot = _snapshot_sources(conn, execution_manifest, sets["residual"], rel_26)

        ot_ids = {int(x) for x in execution_manifest["ot_exclusive_future_2c2b"]["orden_trabajo_ids"]}
        ot_found = _count_ids_exist(conn, "orden_trabajo", ot_ids)
        if ot_found != len(ot_ids):
            errors.append(f"OT future: {ot_found}/{len(ot_ids)}")

    except Exception as exc:
        errors.append(str(exc))
        sets = {"iniciador_ruta": set()}
        sources_snapshot = {}
        unlock_sim = {}
        closure = {}
        acts_148 = set()
        rel_26 = set()

    engine_audit = audit_table_engines(conn, ("iniciador_ruta",))
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
        "safe_set_counts": {
            "iniciador_ruta": len(sets["iniciador_ruta"]),
            "residual": len(sets["residual"]),
            "relevamiento": len(sets["relevamiento"]),
        },
        "route_refs": route_refs,
        "incoming_fk_blockers": fk_blockers,
        "unlock_simulation": unlock_sim,
        "protected_closure": closure,
        "protected_comprobacion_regression": comp_reg,
        "sources_snapshot": sources_snapshot,
        "acts_148_count": len(acts_148),
        "relevamientos_26_count": len(rel_26),
    }


def apply_phase2c2a_initiators_cleanup(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    source_diag_path: Path,
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_prot_hash: str,
    backup_path: str,
    backup_hash: str,
    backup_size: int,
    backup_exit_code: int,
    restore_verified: bool,
    freeze_method: str,
) -> dict[str, Any]:
    """Aplica DELETE FASE 2C.2A en transacción única."""
    sets = _load_ini_sets(execution_manifest)
    ini_ids = sets["iniciador_ruta"]
    acts_148 = {int(x) for x in execution_manifest["excluded"]["acts_148"]}
    rel_26 = {int(x) for x in execution_manifest["excluded"]["relevamientos_26"]}
    ot_future = {int(x) for x in execution_manifest["ot_exclusive_future_2c2b"]["orden_trabajo_ids"]}

    counts_before = {t: _count(conn, t) for t in BASELINE_POST_2C1}

    preflight = preflight_phase2c2a_apply(
        conn,
        execution_manifest,
        protected_manifest,
        source_diag_path,
        confirm_database=confirm_database,
        expected_exec_hash=expected_exec_hash,
        expected_source_diag_hash=expected_source_diag_hash,
        expected_prot_hash=expected_prot_hash,
        backup_confirmed=True,
        restore_verified=restore_verified,
    )
    sources_snapshot = preflight["sources_snapshot"]
    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))

    if conn.in_transaction():
        conn.commit()

    trans = conn.begin()
    cascade_deleted: dict[str, int] = {}
    explicit_deleted: dict[str, int] = {}
    try:
        explicit_deleted["iniciador_ruta"] = _delete_ids(conn, "iniciador_ruta", ini_ids)
        if explicit_deleted["iniciador_ruta"] != EXPECTED_SAFE_TOTAL:
            raise ApplyAbortError(
                f"iniciador deleted {explicit_deleted['iniciador_ruta']} != {EXPECTED_SAFE_TOTAL}"
            )

        remain = _count_ids_exist(conn, "iniciador_ruta", ini_ids)
        if remain:
            raise ApplyAbortError(f"manifest iniciador ids remaining: {remain}")

        if _count(conn, "iniciador_ruta") != POST_INICIADOR:
            raise ApplyAbortError(f"iniciador_ruta post: {_count(conn, 'iniciador_ruta')} != {POST_INICIADOR}")

        for tbl in UNCHANGED_TABLES:
            expected = BASELINE_POST_2C1[tbl]
            actual = _count(conn, tbl)
            if actual != expected:
                raise ApplyAbortError(f"unchanged {tbl}: {actual} != {expected}")

        sources_preserved = _verify_sources_preserved(conn, sources_snapshot)

        unlock_post = _compute_unlock_post_delete(conn, acts_148, rel_26)
        if unlock_post["actuaciones"]["unlocked_count"] != 110:
            raise ApplyAbortError(
                f"acts unlock post: {unlock_post['actuaciones']['unlocked_count']} != 110; "
                f"blocked={unlock_post['actuaciones']['blocked'][:5]}"
            )
        if unlock_post["actuaciones"]["blocked_count"] != 38:
            raise ApplyAbortError(f"acts blocked post: {unlock_post['actuaciones']['blocked_count']} != 38")
        if unlock_post["relevamientos"]["unlocked_count"] != 26:
            raise ApplyAbortError(f"rel unlock post: {unlock_post['relevamientos']}")

        ot_found = _count_ids_exist(conn, "orden_trabajo", ot_future)
        if ot_found != len(ot_future):
            raise ApplyAbortError(f"OT future preserved: {ot_found}/{len(ot_future)}")

        for rid in RELEVAMIENTOS_QA_IDS:
            if not _scalar(conn, "SELECT COUNT(*) FROM relevamiento WHERE id = :id", {"id": rid}):
                raise ApplyAbortError(f"QA relevamiento {rid} missing")
            blockers = _fetch_ids(
                conn, f"SELECT id FROM iniciador_ruta WHERE relevamiento_id = {rid}"
            )
            if blockers:
                raise ApplyAbortError(f"QA relev {rid} still has iniciadores: {blockers}")

        protected_preserved: dict[str, dict[str, int]] = {}
        for entity, min_count in PROTECTED_POSTCONDITION_MIN.items():
            table = _table_for_entity(entity)
            ids = prot.get(entity, set())
            found = _count_ids_exist(conn, table, ids)
            protected_preserved[entity] = {"expected": len(ids), "found": found, "min": min_count}
            if found != len(ids):
                raise ApplyAbortError(f"protected {entity}: {found} != {len(ids)}")
            if found < min_count:
                raise ApplyAbortError(f"protected min {entity}: {found} < {min_count}")

        for cid in PROTECTED_COMP_CLOSURE_8:
            if not _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": cid}):
                raise ApplyAbortError(f"protected comprobacion closure {cid} missing")

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

    counts_after = {t: _count(conn, t) for t in BASELINE_POST_2C1}
    users_unlock = post_commit_user_analysis(conn)

    return {
        "ticket": "PREDEPLOY-CLEANUP.3F.3",
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
            "exit_code": backup_exit_code,
            "restore_verified": restore_verified,
        },
        "counts_before": counts_before,
        "explicit_deleted": explicit_deleted,
        "cascade_deleted": cascade_deleted,
        "counts_after": counts_after,
        "manifest_ids_remaining": {"iniciador_ruta": 0},
        "sources_preserved": sources_preserved,
        "sources_snapshot_before": sources_snapshot,
        "unlock": {
            "actuaciones": unlock_post["actuaciones"],
            "relevamientos": unlock_post["relevamientos"],
            "users": users_unlock,
        },
        "future_2c2b": {
            "actuaciones_110": unlock_post["actuaciones"]["unlocked"],
            "orden_trabajo_110": sorted(ot_future),
            "relevamientos_26": unlock_post["relevamientos"]["unlocked"],
        },
        "protected_preserved": protected_preserved,
        "orphan_checks": orphans,
        "otro_relevador_qa": {
            "current_refs": audit_otro_relevador_qa(conn),
            "verdict": "FUTURE_CATALOG_DELETE_AFTER_2C2B",
        },
        "preflight": preflight,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "phase2c2b_executed": False,
        "phase2c2a_prime_executed": False,
    }
