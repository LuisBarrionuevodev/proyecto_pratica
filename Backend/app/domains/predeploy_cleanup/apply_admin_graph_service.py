"""Aplicación ADMIN-GRAPH: ADMIN-A y ADMIN-B (transacciones independientes)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.admin_graph_diag import _surviving_refs
from app.domains.predeploy_cleanup.admin_graph_manifest_freeze import (
    ADMIN_A_DELETE_ORDER,
    ADMIN_A_EXP_25,
    ADMIN_A_NOTIF_25,
    ADMIN_B_COMP,
    ADMIN_B_DELETE_ORDER,
    ADMIN_B_EXP_IDS,
    ADMIN_B_OFICIO,
    BASELINE_POST_3J2,
    JUZGADO_922,
    POST_ADMIN_A,
    POST_ADMIN_B_AFTER_A,
    SOURCE_DIAG_SHA256,
    _protected_closure_for_entities,
    _validate_admin_a_mapping,
    _validate_admin_b_graph,
    _validate_cascade_zero,
    _validate_expediente_no_incoming,
    _validate_notif_refs_after_exp_delete,
)
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
from app.domains.predeploy_cleanup.sequential_simulator import (
    _chunk_ids,
    _fetch_ids,
    _table_for_entity,
    load_user_fk_columns,
)

EXPECTED_ADMIN_A_HASH = "28b606c845c73b6db061d9352e9cae4e222d95d98cb6c05c8b90c80190446aa8"
EXPECTED_ADMIN_B_HASH = "3518deef1e0b06ade1e8ad0eba7a8e93e5978de8d81f2a0875ddd2746c0fdc8a"
EXPECTED_SOURCE_DIAG_HASH = SOURCE_DIAG_SHA256
EXPECTED_PROT_HASH = "d8a1fda3a10e46dcdb90b22038d73e1e08c76754a59c96dc11cff4377a3b102e"

USERS_FK_FREE_BASELINE = 833

BASELINE_PRE_ADMIN_A = {
    **BASELINE_POST_3J2,
    "expediente": 2940,
    "oficio": 1448,
}

POST_ADMIN_A_COUNTS = {
    "expediente": 2915,
    "notificacion": POST_ADMIN_A["notificacion"],
    "comprobacion": 1530,
    "oficio": 1448,
}

POST_ADMIN_A_REBASELINE = {**BASELINE_PRE_ADMIN_A, **POST_ADMIN_A_COUNTS}

POST_ADMIN_B_COUNTS = {
    "expediente": 2913,
    "notificacion": POST_ADMIN_B_AFTER_A["notificacion"],
    "comprobacion": POST_ADMIN_B_AFTER_A["comprobacion"],
    "oficio": 1447,
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
    "notificacion",
    "expediente",
    "actuaciones",
    "iniciador_ruta",
    "oficio",
    "comprobacion",
)

UNCHANGED_AFTER_A = {
    k: v for k, v in BASELINE_PRE_ADMIN_A.items() if k not in ("expediente", "notificacion")
}


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


def _baseline_check(conn: Connection, expected: dict[str, int], label: str) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    if db != "digitaliza_sandbox":
        raise ApplyAbortError(f"{label}: DATABASE()={db}")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if alembic != "l7m8n9o0p1q2":
        raise ApplyAbortError(f"{label}: alembic={alembic}")
    counts: dict[str, int] = {}
    for table, exp in expected.items():
        actual = _count(conn, table)
        counts[table] = actual
        if actual != exp:
            raise ApplyAbortError(f"{label} baseline {table}: {actual} != {exp}")
    return {"database": db, "alembic_revision": alembic, "counts": counts}


def _verify_manifest_hashes(
    execution_manifest: dict[str, Any],
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_prot_hash: str,
) -> None:
    manifest_for_hash = {k: v for k, v in execution_manifest.items() if not k.startswith("_")}
    computed = manifest_sha256(manifest_for_hash)
    if computed != expected_exec_hash:
        raise ApplyAbortError(f"execution hash {computed} != {expected_exec_hash}")
    if execution_manifest.get("source_diag_sha256") != expected_source_diag_hash:
        raise ApplyAbortError("source_diag_sha256 mismatch")
    if execution_manifest.get("protected_manifest_sha256") != expected_prot_hash:
        raise ApplyAbortError("protected_manifest_sha256 mismatch")


def _load_admin_a_ids(execution_manifest: dict[str, Any]) -> tuple[set[int], set[int]]:
    exp_ids = entity_ids(execution_manifest, "expediente")
    notif_ids = entity_ids(execution_manifest, "notificacion")
    if len(exp_ids) != 25 or exp_ids != set(ADMIN_A_EXP_25):
        raise ApplyAbortError(f"ADMIN-A expediente mismatch: {len(exp_ids)}")
    if len(notif_ids) != 25 or notif_ids != set(ADMIN_A_NOTIF_25):
        raise ApplyAbortError(f"ADMIN-A notificacion mismatch: {len(notif_ids)}")
    return exp_ids, notif_ids


def _load_admin_b_ids(execution_manifest: dict[str, Any]) -> tuple[set[int], set[int], set[int]]:
    exp_ids = entity_ids(execution_manifest, "expediente")
    oficio_ids = entity_ids(execution_manifest, "oficio")
    comp_ids = entity_ids(execution_manifest, "comprobacion")
    if exp_ids != set(ADMIN_B_EXP_IDS):
        raise ApplyAbortError(f"ADMIN-B expediente ids: {exp_ids}")
    if oficio_ids != {ADMIN_B_OFICIO}:
        raise ApplyAbortError(f"ADMIN-B oficio ids: {oficio_ids}")
    if comp_ids != {ADMIN_B_COMP}:
        raise ApplyAbortError(f"ADMIN-B comprobacion ids: {comp_ids}")
    return exp_ids, oficio_ids, comp_ids


def _verify_admin_b_component_preserved(conn: Connection) -> dict[str, Any]:
    checks = {
        "expediente_3103": bool(_scalar(conn, "SELECT COUNT(*) FROM expediente WHERE id=3103")),
        "expediente_3104": bool(_scalar(conn, "SELECT COUNT(*) FROM expediente WHERE id=3104")),
        "oficio_1662": bool(
            _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id=1662 AND numero_oficio='OF8430'")
        ),
        "comprobacion_2289": bool(_scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id=2289")),
        "juzgado_922": bool(_scalar(conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE id=922")),
    }
    if not all(checks.values()):
        raise ApplyAbortError(f"ADMIN-B component not preserved: {checks}")
    return checks


def _verify_protected_preserved(conn: Connection, protected_manifest: dict[str, Any]) -> dict[str, Any]:
    prot = expand_protected_indirect(conn, load_protected_sets(protected_manifest))
    preserved: dict[str, Any] = {}
    for entity, min_count in PROTECTED_POSTCONDITION_MIN.items():
        table = _table_for_entity(entity)
        ids = prot.get(entity, set())
        found = _count_ids_exist(conn, table, ids)
        preserved[entity] = {"expected": len(ids), "found": found, "min_count": min_count}
        if found != len(ids):
            raise ApplyAbortError(f"protected {entity}: {found} != {len(ids)}")
        if found < min_count:
            raise ApplyAbortError(f"protected min {entity}: {found} < {min_count}")
    return preserved


def _juzgado_922_status(conn: Connection) -> dict[str, Any]:
    refs = int(
        _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE juzgado_id = :jz", {"jz": JUZGADO_922}) or 0
    )
    exists = bool(_scalar(conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE id = :jz", {"jz": JUZGADO_922}))
    return {
        "juzgado_id": JUZGADO_922,
        "exists": exists,
        "oficio_refs": refs,
        "fk_free": refs == 0,
        "juzgado_922_fk_free_after_admin_b": refs == 0,
        "status": "READY_FOR_PHASE2E" if refs == 0 else "STILL_REFERENCED",
    }


def verify_post_admin_a_baseline(conn: Connection) -> dict[str, Any]:
    """Rebaseline post-COMMIT ADMIN-A antes de iniciar ADMIN-B."""
    return _baseline_check(conn, POST_ADMIN_A_REBASELINE, "POST-ADMIN-A")


def preflight_admin_a_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_prot_hash: str,
    backup_confirmed: bool = False,
    manifest_paths: list | None = None,
    protected_path: Path | None = None,
) -> dict[str, Any]:
    """Preflight ADMIN-A antes de BEGIN."""
    if not backup_confirmed:
        raise ApplyAbortError("backup_confirmed required")

    _verify_manifest_hashes(
        execution_manifest, expected_exec_hash, expected_source_diag_hash, expected_prot_hash
    )

    baseline = _baseline_check(conn, BASELINE_PRE_ADMIN_A, "ADMIN-A")
    exp_ids, notif_ids = _load_admin_a_ids(execution_manifest)

    stale_exp = validate_ids_exist(conn, "expediente", exp_ids, label="expediente")
    stale_notif = validate_ids_exist(conn, "notificacion", notif_ids, label="notificacion")
    if stale_exp or stale_notif:
        raise ApplyAbortError(f"stale ids")

    mapping = _validate_admin_a_mapping(conn)
    _validate_expediente_no_incoming(conn, exp_ids)
    _validate_notif_refs_after_exp_delete(conn, notif_ids, exp_ids)
    _validate_cascade_zero(conn, "expediente", exp_ids)
    _validate_cascade_zero(conn, "notificacion", notif_ids)

    prot_path = protected_path or Path(execution_manifest["protected_manifest_path"])
    closure = _protected_closure_for_entities(
        conn, prot_path, {"expediente": exp_ids, "notificacion": notif_ids}
    )

    fk_valid = _validate_delete_order_fk(ADMIN_A_DELETE_ORDER, load_fk_edges(conn))
    if not fk_valid.get("valid"):
        raise ApplyAbortError(f"delete order: {fk_valid.get('violations')}")

    test_guard: dict[str, Any] = {}
    if manifest_paths:
        known = _load_known_test_ids_from_manifests(manifest_paths)
        test_guard = _known_test_guard(conn, known)
        if not test_guard["guard_ok"]:
            raise ApplyAbortError("known test guard failed")

    engine_audit = audit_table_engines(conn, tuple(ADMIN_A_DELETE_ORDER))
    if not engine_audit["apply_enabled"]:
        raise ApplyAbortError(f"non-InnoDB: {engine_audit['non_transactional']}")

    _assert_admin_and_fabian(conn)

    return {
        "status": "ADMIN_A_PREFLIGHT_OK",
        "baseline": baseline,
        "mapping_links": len(mapping),
        "protected_closure": closure,
        "known_test_guards": test_guard,
        "admin_b_component_preserved": _verify_admin_b_component_preserved(conn),
    }


def preflight_admin_b_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_manifest: dict[str, Any],
    *,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_prot_hash: str,
    backup_confirmed: bool = False,
    admin_a_committed: bool = False,
    manifest_paths: list | None = None,
    protected_path: Path | None = None,
) -> dict[str, Any]:
    """Preflight ADMIN-B antes de BEGIN."""
    if not backup_confirmed:
        raise ApplyAbortError("backup_confirmed required")
    if not admin_a_committed:
        raise ApplyAbortError("admin_a_committed required")
    if not execution_manifest.get("precondition", {}).get("precondition_requires_admin_a_applied"):
        raise ApplyAbortError("manifest missing admin_a precondition")

    _verify_manifest_hashes(
        execution_manifest, expected_exec_hash, expected_source_diag_hash, expected_prot_hash
    )

    post_a = verify_post_admin_a_baseline(conn)
    exp_ids, oficio_ids, comp_ids = _load_admin_b_ids(execution_manifest)

    graph = _validate_admin_b_graph(conn)
    _validate_expediente_no_incoming(conn, exp_ids)

    of_incoming = _surviving_refs(conn, "oficio", ADMIN_B_OFICIO)
    if of_incoming["total_refs"] != 1:
        raise ApplyAbortError(f"oficio incoming: {of_incoming}")

    comp_refs = _surviving_refs(conn, "comprobacion", ADMIN_B_COMP)
    if comp_refs["total_refs"] != 3:
        raise ApplyAbortError(f"comprobacion refs: {comp_refs}")

    _validate_cascade_zero(conn, "expediente", exp_ids)
    _validate_cascade_zero(conn, "oficio", oficio_ids)
    _validate_cascade_zero(conn, "comprobacion", comp_ids)

    prot_path = protected_path or Path(execution_manifest["protected_manifest_path"])
    closure = _protected_closure_for_entities(
        conn,
        prot_path,
        {"expediente": exp_ids, "oficio": oficio_ids, "comprobacion": comp_ids},
    )

    fk_valid = _validate_delete_order_fk(ADMIN_B_DELETE_ORDER, load_fk_edges(conn))
    if not fk_valid.get("valid"):
        raise ApplyAbortError(f"delete order: {fk_valid.get('violations')}")

    test_guard: dict[str, Any] = {}
    if manifest_paths:
        known = _load_known_test_ids_from_manifests(manifest_paths)
        test_guard = _known_test_guard(conn, known)
        if not test_guard["guard_ok"]:
            raise ApplyAbortError("known test guard failed")

    engine_audit = audit_table_engines(conn, tuple(ADMIN_B_DELETE_ORDER))
    if not engine_audit["apply_enabled"]:
        raise ApplyAbortError(f"non-InnoDB: {engine_audit['non_transactional']}")

    _assert_admin_and_fabian(conn)

    jz_before = _juzgado_922_status(conn)
    if jz_before["oficio_refs"] != 1:
        raise ApplyAbortError(f"juzgado refs before B: {jz_before}")

    return {
        "status": "ADMIN_B_PREFLIGHT_OK",
        "post_admin_a_baseline": post_a,
        "graph": graph,
        "protected_closure": closure,
        "known_test_guards": test_guard,
        "juzgado_922_before": jz_before,
    }


def apply_admin_a_cleanup(
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
    protected_path: Path | None = None,
) -> dict[str, Any]:
    """Aplica DELETE ADMIN-A en transacción única."""
    exp_ids, notif_ids = _load_admin_a_ids(execution_manifest)
    counts_before = {t: _count(conn, t) for t in BASELINE_PRE_ADMIN_A}

    preflight = preflight_admin_a_apply(
        conn,
        execution_manifest,
        protected_manifest,
        expected_exec_hash=expected_exec_hash,
        expected_source_diag_hash=expected_source_diag_hash,
        expected_prot_hash=expected_prot_hash,
        backup_confirmed=True,
        manifest_paths=manifest_paths,
        protected_path=protected_path,
    )

    if not restore_verified:
        raise ApplyAbortError("restore_verified required")

    if conn.in_transaction():
        conn.rollback()

    explicit_deleted: dict[str, int] = {}
    cascade_deleted = {"total": 0}
    set_null_affected = {"total": 0}
    trans = conn.begin()
    try:
        _verify_admin_b_component_preserved(conn)

        explicit_deleted["expediente"] = _delete_ids(conn, "expediente", exp_ids)
        if explicit_deleted["expediente"] != 25:
            raise ApplyAbortError(f"exp deleted {explicit_deleted['expediente']} != 25")
        if _count_ids_exist(conn, "expediente", exp_ids):
            raise ApplyAbortError("exp ids remain")

        for nid in sorted(notif_ids):
            act = _fetch_ids(conn, f"SELECT id FROM actuaciones WHERE notificacion_id = {nid}")
            ini = _fetch_ids(conn, f"SELECT id FROM iniciador_ruta WHERE notificacion_id = {nid}")
            exp_n = int(
                _scalar(conn, "SELECT COUNT(*) FROM expediente WHERE notificacion_id = :nid", {"nid": nid})
                or 0
            )
            if act or ini or exp_n:
                raise ApplyAbortError(f"notif {nid} still referenced act={act} ini={ini} exp={exp_n}")

        explicit_deleted["notificacion"] = _delete_ids(conn, "notificacion", notif_ids)
        if explicit_deleted["notificacion"] != 25:
            raise ApplyAbortError(f"notif deleted {explicit_deleted['notificacion']} != 25")
        if _count_ids_exist(conn, "notificacion", notif_ids):
            raise ApplyAbortError("notif ids remain")

        if _count(conn, "expediente") != POST_ADMIN_A_COUNTS["expediente"]:
            raise ApplyAbortError(f"post expediente: {_count(conn, 'expediente')}")
        if _count(conn, "notificacion") != POST_ADMIN_A_COUNTS["notificacion"]:
            raise ApplyAbortError(f"post notificacion: {_count(conn, 'notificacion')}")

        for tbl, expected in UNCHANGED_AFTER_A.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"unchanged {tbl}: {_count(conn, tbl)} != {expected}")

        _verify_admin_b_component_preserved(conn)
        protected_preserved = _verify_protected_preserved(conn, protected_manifest)
        orphans = check_fk_orphans(conn, ORPHAN_TABLES)
        if orphans:
            raise ApplyAbortError(f"orphans: {orphans[:5]}")

        trans.commit()
        committed = True
        status = "COMMITTED"
    except Exception as exc:
        trans.rollback()
        raise ApplyAbortError(str(exc)) from exc

    counts_after = {t: _count(conn, t) for t in BASELINE_PRE_ADMIN_A}

    return {
        "phase": "ADMIN_A",
        "applied_at": datetime.now().isoformat(),
        "database": confirm_database,
        "freeze_method": freeze_method,
        "manifest_sha256": expected_exec_hash,
        "source_diag_sha256": expected_source_diag_hash,
        "protected_manifest_sha256": expected_prot_hash,
        "backup": {"path": backup_path, "size": backup_size, "sha256": backup_hash, "restore_verified": restore_verified},
        "preflight": preflight,
        "counts_before": counts_before,
        "explicit_deleted": explicit_deleted,
        "cascade_deleted": cascade_deleted,
        "set_null_affected": set_null_affected,
        "counts_after": counts_after,
        "manifest_ids_remaining": {"expediente": 0, "notificacion": 0},
        "admin_b_component_preserved": _verify_admin_b_component_preserved(conn),
        "protected_preserved": protected_preserved,
        "orphan_checks": orphans,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "phase2d_executed": False,
        "phase2e_executed": False,
    }


def apply_admin_b_cleanup(
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
    admin_a_committed: bool = True,
    manifest_paths: list | None = None,
    protected_path: Path | None = None,
) -> dict[str, Any]:
    """Aplica DELETE ADMIN-B en transacción única."""
    exp_ids, oficio_ids, comp_ids = _load_admin_b_ids(execution_manifest)
    counts_before = {
        "expediente": _count(conn, "expediente"),
        "notificacion": _count(conn, "notificacion"),
        "comprobacion": _count(conn, "comprobacion"),
        "oficio": _count(conn, "oficio"),
    }

    preflight = preflight_admin_b_apply(
        conn,
        execution_manifest,
        protected_manifest,
        expected_exec_hash=expected_exec_hash,
        expected_source_diag_hash=expected_source_diag_hash,
        expected_prot_hash=expected_prot_hash,
        backup_confirmed=True,
        admin_a_committed=admin_a_committed,
        manifest_paths=manifest_paths,
        protected_path=protected_path,
    )

    if not restore_verified:
        raise ApplyAbortError("restore_verified required")

    if conn.in_transaction():
        conn.rollback()

    explicit_deleted: dict[str, int] = {}
    cascade_deleted = {"total": 0}
    set_null_affected = {"total": 0}
    trans = conn.begin()
    try:
        explicit_deleted["expediente"] = _delete_ids(conn, "expediente", exp_ids)
        if explicit_deleted["expediente"] != 2:
            raise ApplyAbortError(f"exp deleted {explicit_deleted['expediente']} != 2")
        if _count_ids_exist(conn, "expediente", exp_ids):
            raise ApplyAbortError("exp 3103/3104 remain")

        of_incoming = _surviving_refs(conn, "oficio", ADMIN_B_OFICIO)
        if of_incoming["total_refs"] != 0:
            raise ApplyAbortError(f"oficio still blocked: {of_incoming}")

        explicit_deleted["oficio"] = _delete_ids(conn, "oficio", oficio_ids)
        if explicit_deleted["oficio"] != 1:
            raise ApplyAbortError(f"oficio deleted {explicit_deleted['oficio']} != 1")
        if _count_ids_exist(conn, "oficio", oficio_ids):
            raise ApplyAbortError("oficio 1662 remains")

        comp_refs = _surviving_refs(conn, "comprobacion", ADMIN_B_COMP)
        if comp_refs["total_refs"] != 0:
            raise ApplyAbortError(f"comprobacion still blocked: {comp_refs}")

        explicit_deleted["comprobacion"] = _delete_ids(conn, "comprobacion", comp_ids)
        if explicit_deleted["comprobacion"] != 1:
            raise ApplyAbortError(f"comp deleted {explicit_deleted['comprobacion']} != 1")
        if _count_ids_exist(conn, "comprobacion", comp_ids):
            raise ApplyAbortError("comprobacion 2289 remains")

        for tbl, expected in POST_ADMIN_B_COUNTS.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"post {tbl}: {_count(conn, tbl)} != {expected}")

        for tbl, expected in UNCHANGED_AFTER_A.items():
            if tbl in POST_ADMIN_B_COUNTS:
                continue
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"unchanged {tbl}: {_count(conn, tbl)} != {expected}")

        juzgado_status = _juzgado_922_status(conn)
        if not juzgado_status["exists"]:
            raise ApplyAbortError("juzgado 922 missing")
        if juzgado_status["oficio_refs"] != 0:
            raise ApplyAbortError(f"juzgado refs post-B: {juzgado_status}")

        protected_preserved = _verify_protected_preserved(conn, protected_manifest)
        orphans = check_fk_orphans(conn, ORPHAN_TABLES)
        if orphans:
            raise ApplyAbortError(f"orphans: {orphans[:5]}")

        trans.commit()
        committed = True
        status = "COMMITTED"
    except Exception as exc:
        trans.rollback()
        raise ApplyAbortError(str(exc)) from exc

    counts_after = {
        "expediente": _count(conn, "expediente"),
        "notificacion": _count(conn, "notificacion"),
        "comprobacion": _count(conn, "comprobacion"),
        "oficio": _count(conn, "oficio"),
    }

    return {
        "phase": "ADMIN_B",
        "applied_at": datetime.now().isoformat(),
        "database": confirm_database,
        "freeze_method": freeze_method,
        "manifest_sha256": expected_exec_hash,
        "source_diag_sha256": expected_source_diag_hash,
        "protected_manifest_sha256": expected_prot_hash,
        "precondition_admin_a": {"committed": admin_a_committed},
        "backup": {"path": backup_path, "size": backup_size, "sha256": backup_hash, "restore_verified": restore_verified},
        "preflight": preflight,
        "counts_before": counts_before,
        "explicit_deleted": explicit_deleted,
        "cascade_deleted": cascade_deleted,
        "set_null_affected": set_null_affected,
        "counts_after": counts_after,
        "manifest_ids_remaining": {
            "expediente_3103": 0,
            "expediente_3104": 0,
            "oficio_1662": 0,
            "comprobacion_2289": 0,
        },
        "juzgado_922_status": juzgado_status,
        "protected_preserved": protected_preserved,
        "orphan_checks": orphans,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "phase2d_executed": False,
        "phase2e_executed": False,
    }


def post_commit_user_analysis(conn: Connection) -> dict[str, Any]:
    """Recalcula users test FK-free tras ADMIN-GRAPH completo."""
    test_users = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    fk_columns = load_user_fk_columns(conn)
    deleted_admin = set(ADMIN_A_EXP_25) | set(ADMIN_B_EXP_IDS)
    deleted_notif = set(ADMIN_A_NOTIF_25)
    deleted_oficio = {ADMIN_B_OFICIO}
    deleted_comp = {ADMIN_B_COMP}
    unlocked = 0
    still = 0
    for uid in test_users:
        blocked = False
        for table, col in fk_columns:
            for r in conn.execute(text(f"SELECT id FROM `{table}` WHERE `{col}` = :uid"), {"uid": uid}):
                rid = r[0]
                if table == "expediente" and rid in deleted_admin:
                    continue
                if table == "notificacion" and rid in deleted_notif:
                    continue
                if table == "oficio" and rid in deleted_oficio:
                    continue
                if table == "comprobacion" and rid in deleted_comp:
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
        "users_test_fk_free_baseline": USERS_FK_FREE_BASELINE,
        "users_test_fk_free_after_admin_graph": unlocked,
        "users_additionally_unlocked": unlocked - USERS_FK_FREE_BASELINE,
        "users_test_still_blocked": still,
    }
