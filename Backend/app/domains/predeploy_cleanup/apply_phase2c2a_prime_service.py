"""Aplicación FASE 2C.2A': DELETE 12 ruta_item + 38 iniciador_ruta (transacción única)."""

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
from app.domains.predeploy_cleanup.phase2c2a_prime_wrappers_manifest_freeze import (
    BASELINE_POST_2C2B,
    EXPECTED_INI,
    EXPECTED_RI,
    PHASE2C2A_PRIME_DELETE_ORDER,
    POST_EXPLICIT,
    _baseline_check,
    _protected_comp_regression,
    _validate_iniciadores_after_ri_sim,
    _validate_ruta_item_fks,
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

EXPECTED_EXEC_HASH = "184aaca3496ed0bc55851805c2cbb768eb470987c812c0d5fe58f3b776e2ffdb"
EXPECTED_SOURCE_DIAG_HASH = "59dd11ab7d0f0c85b758df60767ad94bf05f912e24507e2ccaa576ab75f24998"
EXPECTED_PROT_HASH = "d8a1fda3a10e46dcdb90b22038d73e1e08c76754a59c96dc11cff4377a3b102e"

EMPTY_ROUTE_IDS = (
    4938,
    4944,
    5195,
    5199,
    5204,
    5245,
    5261,
    5550,
    5560,
    5574,
    6372,
    6461,
)

UNCHANGED_TABLES = {
    k: v
    for k, v in BASELINE_POST_2C2B.items()
    if k not in POST_EXPLICIT
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
    "ruta_item",
    "ruta_pool_dia",
    "iniciador_ruta",
    "ruta_trabajo",
    "actuaciones",
    "notificacion",
    "comprobacion",
    "expediente",
    "oficio",
    "orden_trabajo",
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
    expected = {"ruta_item": EXPECTED_RI, "iniciador_ruta": EXPECTED_INI}
    sets: dict[str, set[int]] = {}
    for entity in PHASE2C2A_PRIME_DELETE_ORDER:
        ids = entity_ids(execution_manifest, entity)
        if len(ids) != expected[entity]:
            raise ApplyAbortError(f"{entity} count {len(ids)} != {expected[entity]}")
        sets[entity] = ids
    return sets


def _load_preserved_from_manifest(execution_manifest: dict[str, Any]) -> dict[str, Any]:
    excluded = execution_manifest.get("excluded", {})
    preserve = execution_manifest.get("preserve_sources", {})
    future = execution_manifest.get("future_2c2b_prime", {})
    orphan_future = execution_manifest.get("future_orphan_candidates", {})

    acts_38 = {int(x) for x in future.get("actuaciones_38", [])}
    ot_38 = {int(x) for x in future.get("orden_trabajo_38", [])}
    source_119 = {int(x) for x in excluded.get("source_notificaciones_119", [])}
    orphan_notifs = {int(x) for x in excluded.get("orphan_notificaciones_36", [])}
    orphan_comps = {int(x) for x in excluded.get("orphan_comprobaciones_20", [])}

    direct_notifs = {
        int(n["notificacion_id"])
        for n in preserve.get("notificaciones", [])
        if n.get("notificacion_id")
    }
    oficio_chains = preserve.get("oficio_chains", [])
    future_notif_candidates = {int(x) for x in orphan_future.get("notificaciones_25", [])}
    future_comp_candidates = {int(x) for x in orphan_future.get("comprobacion_2289", [])}

    if len(acts_38) != 38 or len(ot_38) != 38:
        raise ApplyAbortError("future acts/ot count mismatch")
    if len(source_119) != 119:
        raise ApplyAbortError("source_119 count mismatch")
    if len(orphan_notifs) != 36 or len(orphan_comps) != 20:
        raise ApplyAbortError("orphan doc count mismatch")
    if len(direct_notifs) != 29:
        raise ApplyAbortError(f"direct notifs {len(direct_notifs)} != 29")

    cls = execution_manifest.get("classification", {})
    if cls.get("safe_test_initiator") != 23 or cls.get("safe_wrapper_around_preserved_source") != 15:
        raise ApplyAbortError("classification mismatch")

    return {
        "acts_38": acts_38,
        "ot_38": ot_38,
        "source_notificaciones_119": source_119,
        "direct_notificaciones_29": direct_notifs,
        "orphan_notificaciones_36": orphan_notifs,
        "orphan_comprobaciones_20": orphan_comps,
        "oficio_chains": oficio_chains,
        "future_notif_candidates": future_notif_candidates,
        "future_comp_candidates": future_comp_candidates,
    }


def _verify_acts_unlocked(conn: Connection, act_ids: set[int]) -> dict[str, Any]:
    unlocked: list[int] = []
    still: list[dict[str, Any]] = []
    for aid in sorted(act_ids):
        inis = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE actuacion_id = {aid}")
        ri = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE actuacion_id = {aid}")
        rp: set[int] = set()
        for iid in inis:
            rp |= _fetch_ids(conn, f"SELECT id FROM ruta_pool_dia WHERE iniciador_ruta_id = {iid}")
        if not inis and not ri and not rp:
            unlocked.append(aid)
        else:
            still.append(
                {
                    "actuacion_id": aid,
                    "iniciadores": sorted(inis),
                    "ruta_items": sorted(ri),
                    "ruta_pool": sorted(rp),
                }
            )
    return {
        "UNLOCKED": len(unlocked),
        "STILL_BLOCKED": len(still),
        "UNLOCKED_ids": unlocked,
        "STILL_BLOCKED_detail": still,
    }


def _verify_oficio_chains(conn: Connection, chains: list[dict[str, Any]]) -> None:
    for chain in chains:
        oid = chain.get("oficio_id")
        if oid and not _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id = :id", {"id": oid}):
            raise ApplyAbortError(f"oficio {oid} missing")
        cid = chain.get("comprobacion_id")
        if cid and not _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": cid}):
            raise ApplyAbortError(f"comprobacion {cid} missing")
        sg = chain.get("chain") or {}
        for exp in sg.get("expedientes", []):
            eid = exp.get("id")
            if eid and not _scalar(conn, "SELECT COUNT(*) FROM expediente WHERE id = :id", {"id": eid}):
                raise ApplyAbortError(f"expediente {eid} missing")


def _verify_empty_routes(conn: Connection, route_ids: tuple[int, ...]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for rtid in route_ids:
        if not _scalar(conn, "SELECT COUNT(*) FROM ruta_trabajo WHERE id = :id", {"id": rtid}):
            raise ApplyAbortError(f"ruta_trabajo {rtid} missing")
        refs = _fetch_ids(conn, f"SELECT id FROM ruta_item WHERE ruta_trabajo_id = {rtid}")
        result.append({"ruta_trabajo_id": rtid, "ruta_item_refs": len(refs)})
        if refs:
            raise ApplyAbortError(f"route {rtid} still has {len(refs)} ruta_item refs")
    return result


def _ruta_pool_refs_to_items(conn: Connection, ri_ids: set[int]) -> int:
    total = 0
    for chunk in _chunk_ids(ri_ids, 300):
        ph = ",".join(str(i) for i in chunk)
        total += int(
            _scalar(conn, f"SELECT COUNT(*) FROM ruta_pool_dia WHERE ruta_item_id IN ({ph})") or 0
        )
    return total


def preflight_phase2c2a_prime_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_prot_hash: str,
    backup_confirmed: bool = False,
) -> dict[str, Any]:
    """Preflight FASE 2C.2A' antes de BEGIN."""
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

    baseline: dict[str, Any] = {}
    entity_sets: dict[str, set[int]] = {}
    preserved: dict[str, Any] = {}
    closure: dict[str, Any] = {}
    comp_reg: dict[str, Any] = {}
    try:
        baseline = _baseline_check(conn)
        entity_sets = _load_entity_sets(execution_manifest)
        preserved = _load_preserved_from_manifest(execution_manifest)

        for entity in PHASE2C2A_PRIME_DELETE_ORDER:
            stale = validate_ids_exist(conn, entity, entity_sets[entity], label=entity)
            if stale:
                errors.append(f"missing {entity}: {stale[:3]}")

        pool_refs = _ruta_pool_refs_to_items(conn, entity_sets["ruta_item"])
        if pool_refs != 0:
            errors.append(f"ruta_pool_dia refs to safe ruta_item: {pool_refs}")

        ri_fk = _validate_ruta_item_fks(conn, entity_sets["ruta_item"])
        ini_fk = _validate_iniciadores_after_ri_sim(
            conn, entity_sets["iniciador_ruta"], entity_sets["ruta_item"]
        )

        if _count_ids_exist(conn, "actuaciones", preserved["acts_38"]) != 38:
            errors.append("future acts not all present")
        if _count_ids_exist(conn, "orden_trabajo", preserved["ot_38"]) != 38:
            errors.append("future OT not all present")

        if _count_ids_exist(conn, "notificacion", preserved["direct_notificaciones_29"]) != 29:
            errors.append("direct source notifs missing")
        if _count_ids_exist(conn, "notificacion", preserved["source_notificaciones_119"]) != 119:
            errors.append("source_119 notifs missing")
        if _count_ids_exist(conn, "notificacion", preserved["orphan_notificaciones_36"]) != 36:
            errors.append("orphan notifs missing")
        if _count_ids_exist(conn, "comprobacion", preserved["orphan_comprobaciones_20"]) != 20:
            errors.append("orphan comps missing")

        _verify_oficio_chains(conn, preserved["oficio_chains"])

        prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
        virtual = VirtualDeleteState()
        virtual.add_explicit("ruta_item", entity_sets["ruta_item"])
        virtual.add_explicit("iniciador_ruta", entity_sets["iniciador_ruta"])
        closure = protection_closure_check(virtual, prot)
        if not closure.get("valid"):
            errors.append("protected closure failed")

        comp_reg = _protected_comp_regression(conn, prot)
        if not comp_reg["all_protected"]:
            errors.append("protected comprobacion regression")

        fk_valid = _validate_delete_order_fk(PHASE2C2A_PRIME_DELETE_ORDER, load_fk_edges(conn))
        if not fk_valid.get("valid"):
            errors.append(f"delete order: {fk_valid.get('violations')}")

        tipo = execution_manifest.get("validation", {}).get("tipo_counts", {})
        if tipo.get("REINSPECCION_NOTIFICACION") != 35 or tipo.get("REINSPECCION_OFICIO") != 3:
            errors.append(f"tipo counts: {tipo}")

    except Exception as exc:
        errors.append(str(exc))

    engine_audit = audit_table_engines(conn, tuple(PHASE2C2A_PRIME_DELETE_ORDER))
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
        "ruta_item_fk": ri_fk,
        "iniciador_fk_after_ri_sim": ini_fk,
        "ruta_pool_refs_to_items": pool_refs,
        "protected_closure": closure,
        "protected_comprobacion_regression": comp_reg,
    }


def apply_phase2c2a_prime_wrappers_cleanup(
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
) -> dict[str, Any]:
    """Aplica DELETE FASE 2C.2A' en transacción única."""
    entity_sets = _load_entity_sets(execution_manifest)
    preserved = _load_preserved_from_manifest(execution_manifest)
    ri_ids = entity_sets["ruta_item"]
    ini_ids = entity_sets["iniciador_ruta"]

    counts_before = {t: _count(conn, t) for t in list(POST_EXPLICIT) + list(UNCHANGED_TABLES)}

    preflight = preflight_phase2c2a_prime_apply(
        conn,
        execution_manifest,
        protected_manifest,
        confirm_database=confirm_database,
        expected_exec_hash=expected_exec_hash,
        expected_source_diag_hash=expected_source_diag_hash,
        expected_prot_hash=expected_prot_hash,
        backup_confirmed=True,
    )

    if not restore_verified:
        raise ApplyAbortError("restore_verified required")

    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    pool_before = _count(conn, "ruta_pool_dia")

    if conn.in_transaction():
        conn.rollback()

    explicit_deleted: dict[str, int] = {}
    cascade_deleted: dict[str, int] = {}
    set_null_affected: dict[str, int] = {"ruta_pool_dia": 0}
    trans = conn.begin()
    try:
        pool_refs_before = _ruta_pool_refs_to_items(conn, ri_ids)
        if pool_refs_before != 0:
            raise ApplyAbortError(f"ruta_pool refs before delete: {pool_refs_before}")

        explicit_deleted["ruta_item"] = _delete_ids(conn, "ruta_item", ri_ids)
        if explicit_deleted["ruta_item"] != EXPECTED_RI:
            raise ApplyAbortError(f"ruta_item deleted {explicit_deleted['ruta_item']} != {EXPECTED_RI}")
        if _count_ids_exist(conn, "ruta_item", ri_ids):
            raise ApplyAbortError("ruta_item ids remain")
        if _count(conn, "ruta_item") != POST_EXPLICIT["ruta_item"]:
            raise ApplyAbortError(f"post ruta_item: {_count(conn, 'ruta_item')}")

        pool_after = _count(conn, "ruta_pool_dia")
        if pool_after != pool_before:
            raise ApplyAbortError(f"ruta_pool_dia changed: {pool_before} -> {pool_after}")
        set_null_affected["ruta_pool_dia"] = 0
        cascade_deleted = {tbl: 0 for tbl in UNCHANGED_TABLES if tbl not in ("ruta_pool_dia",)}

        _validate_iniciadores_after_ri_sim(conn, ini_ids, set())

        explicit_deleted["iniciador_ruta"] = _delete_ids(conn, "iniciador_ruta", ini_ids)
        if explicit_deleted["iniciador_ruta"] != EXPECTED_INI:
            raise ApplyAbortError(
                f"iniciador deleted {explicit_deleted['iniciador_ruta']} != {EXPECTED_INI}"
            )
        if _count_ids_exist(conn, "iniciador_ruta", ini_ids):
            raise ApplyAbortError("iniciador ids remain")
        if _count(conn, "iniciador_ruta") != POST_EXPLICIT["iniciador_ruta"]:
            raise ApplyAbortError(f"post iniciador: {_count(conn, 'iniciador_ruta')}")

        unlock = _verify_acts_unlocked(conn, preserved["acts_38"])
        if unlock["UNLOCKED"] != 38 or unlock["STILL_BLOCKED"] != 0:
            raise ApplyAbortError(f"acts unlock: {unlock['UNLOCKED']}/38 still={unlock['STILL_BLOCKED']}")

        if _count_ids_exist(conn, "orden_trabajo", preserved["ot_38"]) != 38:
            raise ApplyAbortError("future OT not preserved")

        if _count_ids_exist(conn, "notificacion", preserved["direct_notificaciones_29"]) != 29:
            raise ApplyAbortError("direct source notifs not preserved")
        if _count_ids_exist(conn, "notificacion", preserved["source_notificaciones_119"]) != 119:
            raise ApplyAbortError("source_119 not preserved")
        if _count_ids_exist(conn, "notificacion", preserved["orphan_notificaciones_36"]) != 36:
            raise ApplyAbortError("orphan notifs not preserved")
        if _count_ids_exist(conn, "comprobacion", preserved["orphan_comprobaciones_20"]) != 20:
            raise ApplyAbortError("orphan comps not preserved")
        _verify_oficio_chains(conn, preserved["oficio_chains"])

        if preserved["future_notif_candidates"]:
            _count_ids_exist(conn, "notificacion", preserved["future_notif_candidates"])
        if preserved["future_comp_candidates"]:
            if not _scalar(
                conn,
                "SELECT COUNT(*) FROM comprobacion WHERE id = :id",
                {"id": list(preserved["future_comp_candidates"])[0]},
            ):
                raise ApplyAbortError("future comp 2289 missing")

        empty_routes = _verify_empty_routes(conn, EMPTY_ROUTE_IDS)

        for entity in PHASE2C2A_PRIME_DELETE_ORDER:
            if _count_ids_exist(conn, entity, entity_sets[entity]):
                raise ApplyAbortError(f"manifest ids remain: {entity}")

        for tbl, expected in POST_EXPLICIT.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"post {tbl}: {_count(conn, tbl)} != {expected}")

        for tbl, expected in UNCHANGED_TABLES.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"unchanged {tbl}: {_count(conn, tbl)} != {expected}")

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
        "ticket": "PREDEPLOY-CLEANUP.3H.2",
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
        "cascade_deleted": cascade_deleted,
        "set_null_affected": set_null_affected,
        "counts_after": counts_after,
        "manifest_ids_remaining": {e: 0 for e in PHASE2C2A_PRIME_DELETE_ORDER},
        "future_2c2b_prime": {
            "actuaciones_38": sorted(preserved["acts_38"]),
            "orden_trabajo_38": sorted(preserved["ot_38"]),
            "unlocked_acts": unlock,
        },
        "preserved_sources": {
            "direct_notificaciones_29": sorted(preserved["direct_notificaciones_29"]),
            "source_notificaciones_119": sorted(preserved["source_notificaciones_119"]),
            "oficio_chains": preserved["oficio_chains"],
        },
        "current_orphan_docs_preserved": {
            "orphan_notificaciones_36": sorted(preserved["orphan_notificaciones_36"]),
            "orphan_comprobaciones_20": sorted(preserved["orphan_comprobaciones_20"]),
        },
        "future_orphan_candidates_preserved": {
            "notificaciones_25": sorted(preserved["future_notif_candidates"]),
            "comprobacion_2289": sorted(preserved["future_comp_candidates"]),
        },
        "empty_routes_post_prime": empty_routes,
        "protected_preserved": protected_preserved,
        "orphan_checks": orphans,
        "users_unlock": users_unlock,
        "preflight": preflight,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "phase2c2b_prime_executed": False,
        "phase2c2c_executed": False,
        "phase2d_executed": False,
        "phase2e_executed": False,
    }


def post_commit_user_analysis(conn: Connection) -> dict[str, Any]:
    """Recalcula users test FK-free tras FASE 2C.2A'."""
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
        "users_test_fk_free_after_prime": len(unlocked),
        "users_test_still_blocked": len(still_blocked),
        "unlocked_sample": sorted(unlocked)[:40],
    }
