"""Aplicación FASE 2C.2B': DELETE 38 actuaciones + 38 OT (transacción única)."""

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
from app.domains.predeploy_cleanup.phase2c2b_cascade_reconcile import (
    _reconcile_acta_inspeccion_item,
    _reconcile_actuaciones_inspector,
    _reconcile_inspeccion,
    _reconcile_simple_child,
)
from app.domains.predeploy_cleanup.phase2c2b_prime_sources_manifest_freeze import (
    BASELINE_POST_2C2A_PRIME,
    EMPTY_ROUTE_IDS,
    EXPECTED_ACTS,
    EXPECTED_CASCADE_PHYSICAL,
    EXPECTED_OT,
    PHASE2C2B_PRIME_DELETE_ORDER,
    POST_EXPLICIT,
    USERS_FK_FREE_POST_2C2A_PRIME,
    _baseline_check,
)
from app.domains.predeploy_cleanup.phase2c2b_sources_manifest_freeze import (
    _protected_comp_regression,
    _rows_fk_to_ot,
    _validate_act_blockers,
    _validate_ot_exclusive,
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

EXPECTED_EXEC_HASH = "a78737957310d0fc90899e399a7a16b1b09cc96a181c7e1560b70e02180d6ac6"
EXPECTED_APPLY_2C2A_PRIME_HASH = "dd82505c222bc9e055fa182aa164f2473584797948b6dae9008fbe2831f03ac6"
EXPECTED_SOURCE_DIAG_3H_HASH = "59dd11ab7d0f0c85b758df60767ad94bf05f912e24507e2ccaa576ab75f24998"
EXPECTED_PROT_HASH = "d8a1fda3a10e46dcdb90b22038d73e1e08c76754a59c96dc11cff4377a3b102e"

CHILD_TABLES = ("inspeccion", "actuaciones_inspector", "acta_inspeccion_item", "clausura", "decomiso")

UNCHANGED_TABLES = {
    k: v
    for k, v in BASELINE_POST_2C2A_PRIME.items()
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
    "actuaciones",
    "orden_trabajo",
    "notificacion",
    "comprobacion",
    "expediente",
    "oficio",
    "iniciador_ruta",
    "ruta_item",
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


def _load_entity_sets(execution_manifest: dict[str, Any]) -> dict[str, set[int]]:
    expected = {"actuaciones": EXPECTED_ACTS, "orden_trabajo": EXPECTED_OT}
    sets: dict[str, set[int]] = {}
    for entity in PHASE2C2B_PRIME_DELETE_ORDER:
        ids = entity_ids(execution_manifest, entity)
        if len(ids) != expected[entity]:
            raise ApplyAbortError(f"{entity} count {len(ids)} != {expected[entity]}")
        sets[entity] = ids
    return sets


def _load_preserved_from_manifest(execution_manifest: dict[str, Any]) -> dict[str, Any]:
    parent = execution_manifest.get("preserve_parent_documents", {})
    source = execution_manifest.get("preserve_source_documents", {})
    excluded = execution_manifest.get("excluded", {})
    future_orphan = execution_manifest.get("future_orphan_documents_after_apply", {})

    parent_notifs = {int(x) for x in parent.get("notificacion_ids", [])}
    parent_comps = {int(x) for x in parent.get("comprobacion_ids", [])}
    direct_notifs = {int(x) for x in source.get("direct_notificaciones_29", [])}
    source_119 = {int(x) for x in source.get("source_notificaciones_119", [])}
    orphan_36 = {int(x) for x in excluded.get("orphan_notificaciones_36", [])}
    orphan_20 = {int(x) for x in excluded.get("orphan_comprobaciones_20", [])}
    expected_new_notif = future_orphan.get("NEW_ORPHAN_NOTIFICACION_AFTER_2C2B_PRIME", [])
    expected_new_comp = future_orphan.get("NEW_ORPHAN_COMPROBACION_AFTER_2C2B_PRIME", [])

    if len(parent_notifs) != 25 or len(parent_comps) != 1:
        raise ApplyAbortError(f"parent docs: notif={len(parent_notifs)} comp={len(parent_comps)}")
    if parent_comps != {2289}:
        raise ApplyAbortError("parent comp != 2289")
    if len(direct_notifs) != 29 or len(source_119) != 119:
        raise ApplyAbortError("source doc count mismatch")
    if len(orphan_36) != 36 or len(orphan_20) != 20:
        raise ApplyAbortError("existing orphan count mismatch")

    fam = execution_manifest.get("act_family_breakdown", {})
    if fam.get("SET_ACT_OLD_count") != 38 or fam.get("SET_ACT_STRUCTURED_count") != 0:
        raise ApplyAbortError("family mismatch")

    return {
        "parent_notificaciones_25": parent_notifs,
        "parent_comprobacion_2289": parent_comps,
        "direct_notificaciones_29": direct_notifs,
        "source_notificaciones_119": source_119,
        "oficio_chains": source.get("oficio_chains", []),
        "orphan_notificaciones_36": orphan_36,
        "orphan_comprobaciones_20": orphan_20,
        "expected_new_orphan_notif": [int(x) for x in expected_new_notif],
        "expected_new_orphan_comp": [int(x) for x in expected_new_comp],
    }


def _recalc_cascade_physical(conn: Connection, act_ids: set[int]) -> dict[str, int]:
    insp = _reconcile_inspeccion(conn, act_ids)
    ai = _reconcile_actuaciones_inspector(conn, act_ids)
    cl = _reconcile_simple_child(conn, "clausura", "actuacion_id", act_ids)
    de = _reconcile_simple_child(conn, "decomiso", "actuacion_id", act_ids)
    aii = _reconcile_acta_inspeccion_item(conn, set(insp["inspeccion_ids"]))
    return {
        "inspeccion": insp["physical_rows"],
        "actuaciones_inspector": ai["physical_rows"],
        "clausura": cl["physical_rows"],
        "decomiso": de["physical_rows"],
        "acta_inspeccion_item": aii["physical_rows"],
    }


def _verify_parent_docs(conn: Connection, preserved: dict[str, Any]) -> None:
    if _count_ids_exist(conn, "notificacion", preserved["parent_notificaciones_25"]) != 25:
        raise ApplyAbortError("parent notifs missing")
    if not _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": 2289}):
        raise ApplyAbortError("parent comp 2289 missing")


def _verify_source_docs(conn: Connection, preserved: dict[str, Any]) -> None:
    if _count_ids_exist(conn, "notificacion", preserved["direct_notificaciones_29"]) != 29:
        raise ApplyAbortError("direct source notifs missing")
    if _count_ids_exist(conn, "notificacion", preserved["source_notificaciones_119"]) != 119:
        raise ApplyAbortError("source_119 missing")
    for chain in preserved["oficio_chains"]:
        oid = chain.get("oficio_id")
        if oid and not _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id = :id", {"id": oid}):
            raise ApplyAbortError(f"oficio {oid} missing")
        cid = chain.get("comprobacion_id")
        if cid and not _scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = :id", {"id": cid}):
            raise ApplyAbortError(f"comprobacion {cid} missing")


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


def _recalc_new_orphans_post_apply(
    conn: Connection,
    parent_notifs: set[int],
    parent_comps: set[int],
) -> dict[str, Any]:
    """Notifs/comps parent que quedan sin refs de actuación tras DELETE."""
    orphan_notifs: list[int] = []
    orphan_comps: list[int] = []
    for nid in sorted(parent_notifs):
        refs = int(
            _scalar(conn, "SELECT COUNT(*) FROM actuaciones WHERE notificacion_id = :id", {"id": nid}) or 0
        )
        if refs == 0:
            orphan_notifs.append(nid)
    for cid in sorted(parent_comps):
        refs = int(
            _scalar(conn, "SELECT COUNT(*) FROM actuaciones WHERE comprobacion_id = :id", {"id": cid}) or 0
        )
        if refs == 0:
            orphan_comps.append(cid)
    return {
        "notificaciones": orphan_notifs,
        "comprobaciones": orphan_comps,
    }


def preflight_phase2c2b_prime_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_apply_2c2a_prime_hash: str,
    expected_source_diag_3h_hash: str,
    expected_prot_hash: str,
    backup_confirmed: bool = False,
) -> dict[str, Any]:
    """Preflight FASE 2C.2B' antes de BEGIN."""
    errors: list[str] = []

    if not backup_confirmed:
        errors.append("backup_confirmed required")

    manifest_for_hash = {k: v for k, v in execution_manifest.items() if not k.startswith("_")}
    computed = manifest_sha256(manifest_for_hash)
    if computed != expected_exec_hash:
        errors.append(f"execution hash {computed} != {expected_exec_hash}")
    if execution_manifest.get("source_apply_2c2a_prime_sha256") != expected_apply_2c2a_prime_hash:
        errors.append("source_apply_2c2a_prime_sha256 mismatch")
    if execution_manifest.get("source_diag_3h_sha256") != expected_source_diag_3h_hash:
        errors.append("source_diag_3h_sha256 mismatch")
    if execution_manifest.get("protected_manifest_sha256") != expected_prot_hash:
        errors.append("protected_manifest_sha256 mismatch")

    cascade_physical: dict[str, int] = {}
    closure: dict[str, Any] = {}
    comp_reg: dict[str, Any] = {}
    try:
        baseline = _baseline_check(conn)
        entity_sets = _load_entity_sets(execution_manifest)
        preserved = _load_preserved_from_manifest(execution_manifest)

        for entity in PHASE2C2B_PRIME_DELETE_ORDER:
            stale = validate_ids_exist(conn, entity, entity_sets[entity], label=entity)
            if stale:
                errors.append(f"missing {entity}: {stale[:3]}")

        _validate_act_blockers(conn, entity_sets["actuaciones"])

        prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
        if entity_sets["actuaciones"] & prot.get("actuaciones", set()):
            errors.append("protected act intersection")

        ot_val = _validate_ot_exclusive(
            conn, entity_sets["orden_trabajo"], entity_sets["actuaciones"], prot
        )

        cascade_physical = _recalc_cascade_physical(conn, entity_sets["actuaciones"])
        for tbl, spec in EXPECTED_CASCADE_PHYSICAL.items():
            if cascade_physical.get(tbl, -1) != spec["physical_rows"]:
                errors.append(f"cascade {tbl}: {cascade_physical.get(tbl)}")

        _verify_parent_docs(conn, preserved)
        _verify_source_docs(conn, preserved)

        if _count_ids_exist(conn, "notificacion", preserved["orphan_notificaciones_36"]) != 36:
            errors.append("orphan notifs missing")
        if _count_ids_exist(conn, "comprobacion", preserved["orphan_comprobaciones_20"]) != 20:
            errors.append("orphan comps missing")

        _verify_empty_routes(conn)

        virtual = VirtualDeleteState()
        virtual.add_explicit("actuaciones", entity_sets["actuaciones"])
        virtual.add_explicit("orden_trabajo", entity_sets["orden_trabajo"])
        closure = protection_closure_check(virtual, prot)
        if not closure.get("valid"):
            errors.append("protected closure failed")

        comp_reg = _protected_comp_regression(conn, prot)
        if not comp_reg["all_protected"]:
            errors.append("protected comprobacion regression")

        fk_valid = _validate_delete_order_fk(PHASE2C2B_PRIME_DELETE_ORDER, load_fk_edges(conn))
        if not fk_valid.get("valid"):
            errors.append(f"delete order: {fk_valid.get('violations')}")

    except Exception as exc:
        errors.append(str(exc))
        baseline = {}

    engine_audit = audit_table_engines(conn, tuple(PHASE2C2B_PRIME_DELETE_ORDER))
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
        "ot_exclusive": ot_val,
        "protected_closure": closure,
        "protected_comprobacion_regression": comp_reg,
    }


def apply_phase2c2b_prime_sources_cleanup(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    confirm_database: str,
    expected_exec_hash: str,
    expected_apply_2c2a_prime_hash: str,
    expected_source_diag_3h_hash: str,
    expected_prot_hash: str,
    backup_path: str,
    backup_hash: str,
    backup_size: int,
    restore_verified: bool,
    freeze_method: str,
) -> dict[str, Any]:
    """Aplica DELETE FASE 2C.2B' en transacción única."""
    entity_sets = _load_entity_sets(execution_manifest)
    preserved = _load_preserved_from_manifest(execution_manifest)
    act_ids = entity_sets["actuaciones"]
    ot_ids = entity_sets["orden_trabajo"]

    counts_before = {t: _count(conn, t) for t in list(POST_EXPLICIT) + list(UNCHANGED_TABLES)}

    preflight = preflight_phase2c2b_prime_apply(
        conn,
        execution_manifest,
        protected_manifest,
        confirm_database=confirm_database,
        expected_exec_hash=expected_exec_hash,
        expected_apply_2c2a_prime_hash=expected_apply_2c2a_prime_hash,
        expected_source_diag_3h_hash=expected_source_diag_3h_hash,
        expected_prot_hash=expected_prot_hash,
        backup_confirmed=True,
    )

    if not restore_verified:
        raise ApplyAbortError("restore_verified required")

    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    expected_cascades = _recalc_cascade_physical(conn, act_ids)
    child_before = {t: _count(conn, t) for t in CHILD_TABLES}

    if conn.in_transaction():
        conn.rollback()

    explicit_deleted: dict[str, int] = {}
    cascade_deleted: dict[str, int] = {}
    trans = conn.begin()
    try:
        explicit_deleted["actuaciones"] = _delete_ids(conn, "actuaciones", act_ids)
        if explicit_deleted["actuaciones"] != EXPECTED_ACTS:
            raise ApplyAbortError(f"acts deleted {explicit_deleted['actuaciones']} != {EXPECTED_ACTS}")
        if _count_ids_exist(conn, "actuaciones", act_ids):
            raise ApplyAbortError("act ids remain")

        for tbl in CHILD_TABLES:
            after = _count(conn, tbl)
            deleted_n = child_before[tbl] - after
            expected = expected_cascades.get(tbl, 0)
            if deleted_n != expected:
                raise ApplyAbortError(f"cascade {tbl}: deleted {deleted_n} != {expected}")
            expected_after = EXPECTED_CASCADE_PHYSICAL[tbl]["expected_after"]
            if after != expected_after:
                raise ApplyAbortError(f"post child {tbl}: {after} != {expected_after}")
            cascade_deleted[tbl] = deleted_n

        _verify_parent_docs(conn, preserved)
        _verify_source_docs(conn, preserved)

        for ot_id in sorted(ot_ids):
            acts_on = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE orden_trabajo_id = {ot_id}")
            if acts_on:
                raise ApplyAbortError(f"OT {ot_id} still has acts: {acts_on}")
            refs = _rows_fk_to_ot(conn, ot_id)
            non_zero = {k: v for k, v in refs.items() if v}
            if non_zero:
                raise ApplyAbortError(f"OT {ot_id} refs: {non_zero}")

        explicit_deleted["orden_trabajo"] = _delete_ids(conn, "orden_trabajo", ot_ids)
        if explicit_deleted["orden_trabajo"] != EXPECTED_OT:
            raise ApplyAbortError(f"ot deleted {explicit_deleted['orden_trabajo']} != {EXPECTED_OT}")
        if _count_ids_exist(conn, "orden_trabajo", ot_ids):
            raise ApplyAbortError("ot ids remain")

        for entity in PHASE2C2B_PRIME_DELETE_ORDER:
            if _count_ids_exist(conn, entity, entity_sets[entity]):
                raise ApplyAbortError(f"manifest ids remain: {entity}")

        for tbl, expected in POST_EXPLICIT.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"post {tbl}: {_count(conn, tbl)} != {expected}")

        for tbl, expected in UNCHANGED_TABLES.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"unchanged {tbl}: {_count(conn, tbl)} != {expected}")

        new_orphans = _recalc_new_orphans_post_apply(
            conn,
            preserved["parent_notificaciones_25"],
            preserved["parent_comprobacion_2289"],
        )

        if _count_ids_exist(conn, "notificacion", preserved["orphan_notificaciones_36"]) != 36:
            raise ApplyAbortError("existing orphan notifs not preserved")
        if _count_ids_exist(conn, "comprobacion", preserved["orphan_comprobaciones_20"]) != 20:
            raise ApplyAbortError("existing orphan comps not preserved")

        empty_routes = _verify_empty_routes(conn)

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
        "ticket": "PREDEPLOY-CLEANUP.3H.4",
        "applied_at": datetime.now().isoformat(),
        "database": confirm_database,
        "alembic_revision": preflight["baseline"]["alembic_revision"],
        "freeze_method": freeze_method,
        "manifest_path": str(execution_manifest.get("_source_path", "")),
        "manifest_sha256": expected_exec_hash,
        "source_apply_2c2a_prime_sha256": expected_apply_2c2a_prime_hash,
        "source_diag_3h_sha256": expected_source_diag_3h_hash,
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
        "counts_after": counts_after,
        "manifest_ids_remaining": {e: 0 for e in PHASE2C2B_PRIME_DELETE_ORDER},
        "preserved_parent_docs": {
            "notificaciones_25": sorted(preserved["parent_notificaciones_25"]),
            "comprobacion_2289": 2289,
        },
        "preserved_source_docs": {
            "direct_notificaciones_29": sorted(preserved["direct_notificaciones_29"]),
            "source_notificaciones_119_count": len(preserved["source_notificaciones_119"]),
            "oficio_chains_count": len(preserved["oficio_chains"]),
        },
        "existing_orphans_preserved": {
            "orphan_notificaciones_36": sorted(preserved["orphan_notificaciones_36"]),
            "orphan_comprobaciones_20": sorted(preserved["orphan_comprobaciones_20"]),
        },
        "new_orphans_post_apply": new_orphans,
        "empty_routes_residual": empty_routes,
        "protected_preserved": protected_preserved,
        "orphan_checks": orphans,
        "users_unlock": users_unlock,
        "preflight": preflight,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "phase2c2c_executed": False,
        "phase2d_executed": False,
        "phase2e_executed": False,
    }


def post_commit_user_analysis(conn: Connection) -> dict[str, Any]:
    """Recalcula users test FK-free tras FASE 2C.2B'."""
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
        "users_test_fk_free_baseline_post_2c2a_prime": USERS_FK_FREE_POST_2C2A_PRIME,
        "users_test_fk_free_after_2c2b_prime": len(unlocked),
        "users_additionally_unlocked": len(unlocked) - USERS_FK_FREE_POST_2C2A_PRIME,
        "users_test_still_blocked": len(still_blocked),
    }
