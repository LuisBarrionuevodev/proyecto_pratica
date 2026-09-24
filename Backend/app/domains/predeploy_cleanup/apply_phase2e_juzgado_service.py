"""Aplicación FASE 2E-J: DELETE juzgado_catalogo id=922 (transacción única)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.catalogos.canonical.juzgados import JUZGADOS_CANONICOS
from app.domains.predeploy_cleanup.apply_service import (
    ApplyAbortError,
    _assert_admin_and_fabian,
    _count_ids_exist,
    audit_table_engines,
)
from app.domains.predeploy_cleanup.catalogs_phase2e_manifest_freeze import (
    BASELINE_POST_3L2,
    BLOCKED_QA_CALLE_IDS,
    BLOCKED_TEST_JUZGADO_COUNT,
    CALLE_ALIAS_KEEP_IDS,
    EXPECTED_JUZGADO_CODIGO,
    EXPECTED_JUZGADO_NOMBRE,
    INDETERMINATE_JUZGADO_COUNT,
    JUZGADO_PROVENANCE,
    JUZGADO_SAFE_ID,
    PASAJE_INDEPENDENCIA_ID,
    PROTECTED_JUZGADO_IDS,
    RELEVADOR_SAFE_ID,
    _incoming_fk_schema,
    _operational_guards,
    _protected_closure_check,
    _protected_juzgado_ids,
    _refs_for_parent_id,
    _validate_juzgado_id922,
)
from app.domains.predeploy_cleanup.manifest_io import (
    entity_ids,
    load_manifest,
    manifest_sha256,
    validate_ids_exist,
)
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets

EXPECTED_EXEC_HASH = "99a512014541088f75df02a8c482325ba10c9a8dcfd406eed5a0a6a3219b6a01"
EXPECTED_SOURCE_DIAG_HASH = "d9beb74d93d0280163523b851785e68a2c8307bdfc018f46018027652c5fa4e7"
EXPECTED_PROT_HASH = "d8a1fda3a10e46dcdb90b22038d73e1e08c76754a59c96dc11cff4377a3b102e"

BASELINE_POST_2E_R = {**BASELINE_POST_3L2, "relevador": 10}
CATALOG_PHYSICAL_POST_2E_R = {
    "relevador": 10,
    "juzgado_catalogo": 843,
    "calle_catalogo": 744,
    "rubro": 1224,
}

JUZGADO_CANONICAL_CODES = frozenset(c for c, _ in JUZGADOS_CANONICOS)

PROTECTED_POSTCONDITION_MIN = {
    "actuaciones": 1189,
    "orden_trabajo": 1176,
    "inspeccion": 170,
    "notificacion": 168,
    "comprobacion": 56,
    "oficio": 40,
    "expediente": 40,
}

STOP_SETS_RUBRO = {
    "CANONICAL": 29,
    "CONFIRMADO_TEST_BLOCKED": 669,
    "LEGACY_REAL_KEEP": 515,
    "INDETERMINATE": 11,
}


def _count(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _baseline_check_post_2e_r(conn: Connection) -> dict[str, Any]:
    """Valida baseline operativo post-2E-R."""
    db = _scalar(conn, "SELECT DATABASE()")
    if db != "digitaliza_sandbox":
        raise ApplyAbortError(f"DATABASE()={db}")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if alembic != "l7m8n9o0p1q2":
        raise ApplyAbortError(f"alembic={alembic}")

    counts: dict[str, int] = {}
    drift: list[str] = []
    for table, expected in BASELINE_POST_2E_R.items():
        actual = _count(conn, table)
        counts[table] = actual
        if actual != expected:
            drift.append(f"{table}: {actual} != {expected}")
    for table, expected in CATALOG_PHYSICAL_POST_2E_R.items():
        actual = _count(conn, table)
        counts[table] = actual
        if actual != expected:
            drift.append(f"{table}: {actual} != {expected}")

    if drift:
        raise ApplyAbortError(f"baseline drift: {drift}")

    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "baseline_ok": True,
        "drift": [],
    }


def _validate_execution_precondition(conn: Connection, execution_manifest: dict[str, Any]) -> dict[str, Any]:
    pre = execution_manifest.get("execution_precondition", {})
    if not pre.get("phase2e_r_applied"):
        raise ApplyAbortError("phase2e_r_applied != true")
    if pre.get("relevador_count") != 10:
        raise ApplyAbortError(f"relevador_count={pre.get('relevador_count')}")
    if pre.get("juzgado_catalogo_before") != 843:
        raise ApplyAbortError("juzgado_catalogo_before != 843")
    if _count(conn, "relevador") != 10:
        raise ApplyAbortError("relevador != 10")
    if _count(conn, "juzgado_catalogo") != 843:
        raise ApplyAbortError("juzgado_catalogo != 843")
    rel2 = int(_scalar(conn, "SELECT COUNT(*) FROM relevador WHERE id = :id", {"id": RELEVADOR_SAFE_ID}) or 0)
    if rel2 != 0:
        raise ApplyAbortError("relevador id2 still exists")
    return pre


def _load_juzgado_id(execution_manifest: dict[str, Any]) -> set[int]:
    ids = entity_ids(execution_manifest, "juzgado_catalogo")
    if ids != {JUZGADO_SAFE_ID}:
        raise ApplyAbortError(f"juzgado entities {ids} != {{{JUZGADO_SAFE_ID}}}")
    frozen = set(execution_manifest.get("entities", {}).get("juzgado_catalogo", []))
    if frozen != ids:
        raise ApplyAbortError("entity_ids != manifest entities.juzgado_catalogo")
    return ids


def _validate_identity_snapshot(execution_manifest: dict[str, Any]) -> dict[str, Any]:
    snap = execution_manifest.get("identity_snapshot", [])
    if len(snap) != 1 or snap[0]["id"] != JUZGADO_SAFE_ID:
        raise ApplyAbortError("identity_snapshot invalid")
    row = snap[0]
    if row.get("codigo") != EXPECTED_JUZGADO_CODIGO:
        raise ApplyAbortError(f"identity codigo={row.get('codigo')}")
    if row.get("nombre") != EXPECTED_JUZGADO_NOMBRE:
        raise ApplyAbortError(f"identity nombre={row.get('nombre')}")
    if row.get("classification") != "CONFIRMADO_TEST_FK_FREE":
        raise ApplyAbortError("identity classification mismatch")
    prov = set(row.get("provenance") or [])
    if prov != set(JUZGADO_PROVENANCE):
        raise ApplyAbortError(f"identity provenance={prov}")
    return row


def _oficio_1662_guard(conn: Connection) -> dict[str, Any]:
    exists = bool(_scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id = 1662"))
    if exists:
        raise ApplyAbortError("oficio 1662 still exists")
    return {"oficio_id": 1662, "exists": False, "deleted_in_admin_b": True}


def _validate_canonical_juzgados(conn: Connection) -> dict[str, Any]:
    missing: list[str] = []
    present: list[str] = []
    for codigo, _ in JUZGADOS_CANONICOS:
        found = _scalar(
            conn,
            "SELECT COUNT(*) FROM juzgado_catalogo WHERE codigo = :c AND id != :id",
            {"c": codigo, "id": JUZGADO_SAFE_ID},
        )
        if found:
            present.append(codigo)
        else:
            missing.append(codigo)
    if missing:
        raise ApplyAbortError(f"canonical juzgados missing: {missing}")
    return {"canonical_codes_present": present, "canonical_missing": 0, "count": 15}


def _validate_stop_sets(conn: Connection) -> dict[str, Any]:
    """Verifica que conjuntos STOP 2E-C/2E-U no fueron alterados pre-apply."""
    for cid in BLOCKED_QA_CALLE_IDS:
        if not _scalar(conn, "SELECT COUNT(*) FROM calle_catalogo WHERE id = :id", {"id": cid}):
            raise ApplyAbortError(f"calle QA {cid} missing")
    for aid in CALLE_ALIAS_KEEP_IDS:
        if not _scalar(conn, "SELECT COUNT(*) FROM calle_catalogo WHERE id = :id", {"id": aid}):
            raise ApplyAbortError(f"calle alias {aid} missing")
    if not _scalar(
        conn, "SELECT COUNT(*) FROM calle_catalogo WHERE id = :id", {"id": PASAJE_INDEPENDENCIA_ID}
    ):
        raise ApplyAbortError("pasaje independencia 368 missing")
    if _count(conn, "rubro") != CATALOG_PHYSICAL_POST_2E_R["rubro"]:
        raise ApplyAbortError("rubro count drift")
    return {
        "2e_c": {
            "safe": 0,
            "blocked_qa_ids": list(BLOCKED_QA_CALLE_IDS),
            "alias_keep_ids": list(CALLE_ALIAS_KEEP_IDS),
            "indeterminate_id": PASAJE_INDEPENDENCIA_ID,
        },
        "2e_u": {"safe": 0, "classification_snapshot": STOP_SETS_RUBRO},
    }


def _count_juzgado_classification_snapshot(conn: Connection, diag_data: dict[str, Any]) -> dict[str, Any]:
    """Verifica buckets congelados del diag (excluyendo id a borrar)."""
    jz = diag_data.get("juzgados", {})
    blocked = set(jz.get("BLOCKED_TEST_JUZGADOS", []))
    indeterminate = set(jz.get("INDETERMINATE_JUZGADOS", []))
    if JUZGADO_SAFE_ID in blocked or JUZGADO_SAFE_ID in indeterminate:
        raise ApplyAbortError("id922 in blocked/indeterminate bucket")
    if len(blocked) != BLOCKED_TEST_JUZGADO_COUNT:
        raise ApplyAbortError(f"blocked count {len(blocked)}")
    if len(indeterminate) != INDETERMINATE_JUZGADO_COUNT:
        raise ApplyAbortError(f"indeterminate count {len(indeterminate)}")
    blocked_exist = sum(
        1
        for jid in blocked
        if _scalar(conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE id = :id", {"id": jid})
    )
    indet_exist = sum(
        1
        for jid in indeterminate
        if _scalar(conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE id = :id", {"id": jid})
    )
    return {
        "blocked_test_count": len(blocked),
        "blocked_test_present": blocked_exist,
        "indeterminate_count": len(indeterminate),
        "indeterminate_present": indet_exist,
    }


def _check_juzgado_orphans(conn: Connection, fk_schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
    orphans: list[dict[str, Any]] = []
    for edge in fk_schema:
        tbl = edge["child_table"]
        col = edge["child_column"]
        cnt = int(
            _scalar(
                conn,
                f"""
                SELECT COUNT(*) FROM `{tbl}` c
                LEFT JOIN juzgado_catalogo j ON c.`{col}` = j.id
                WHERE c.`{col}` IS NOT NULL AND j.id IS NULL
                """,
            )
            or 0
        )
        if cnt:
            orphans.append({"child_table": tbl, "child_column": col, "orphan_count": cnt})
    return orphans


def preflight_phase2e_juzgado_apply(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_path: Path,
    *,
    expected_exec_hash: str,
    expected_source_diag_hash: str,
    expected_prot_hash: str,
    backup_confirmed: bool = False,
    restore_verified: bool = False,
    manifest_paths: list | None = None,
    diag_data: dict[str, Any] | None = None,
    phase2e_r_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Preflight 2E-J antes de BEGIN."""
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

    if phase2e_r_report:
        if phase2e_r_report.get("transaction_status") != "COMMITTED":
            errors.append("2E-R not committed")
        if not phase2e_r_report.get("phase2e_r_executed"):
            errors.append("phase2e_r_executed false")
        if phase2e_r_report.get("phase2e_j_executed"):
            errors.append("phase2e_j already executed")

    closure: dict[str, Any] = {}
    test_guard: dict[str, Any] = {}
    juzgado_audit: dict[str, Any] = {}

    try:
        baseline = _baseline_check_post_2e_r(conn)
        precondition = _validate_execution_precondition(conn, execution_manifest)
        delete_ids = _load_juzgado_id(execution_manifest)
        identity = _validate_identity_snapshot(execution_manifest)

        stale = validate_ids_exist(conn, "juzgado_catalogo", delete_ids, label="juzgado")
        if stale:
            errors.append(f"missing juzgado: {stale}")

        _oficio_1662_guard(conn)

        protected_jz = _protected_juzgado_ids(conn, protected_path)
        if protected_jz != set(PROTECTED_JUZGADO_IDS):
            errors.append(f"protected_juzgado_ids drift: {sorted(protected_jz)}")

        if diag_data is None:
            errors.append("diag_data required")
        else:
            juzgado_audit = _validate_juzgado_id922(conn, diag_data, protected_jz)
            bucket_snap = _count_juzgado_classification_snapshot(conn, diag_data)

        fk_schema = _incoming_fk_schema(conn, "juzgado_catalogo")
        fk_validation = _refs_for_parent_id(conn, "juzgado_catalogo", JUZGADO_SAFE_ID, fk_schema)
        if not fk_validation["valid_fk_free"]:
            errors.append(f"id922 FK refs: {fk_validation}")

        canonical = _validate_canonical_juzgados(conn)
        stop_sets = _validate_stop_sets(conn)

        for pid in PROTECTED_JUZGADO_IDS:
            if not _scalar(conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE id = :id", {"id": pid}):
                errors.append(f"protected juzgado {pid} missing")

        closure = _protected_closure_check(conn, protected_path, "juzgado_catalogo", delete_ids)

        if manifest_paths:
            test_guard = _operational_guards(conn, manifest_paths)
            if test_guard.get("safe_users_2d_remaining", 0) != 0:
                errors.append("safe_users_2d_remaining != 0")

        rel2 = _scalar(conn, "SELECT COUNT(*) FROM relevador WHERE id = :id", {"id": RELEVADOR_SAFE_ID})
        if rel2:
            errors.append("relevador id2 exists post-2E-R")

    except Exception as exc:
        errors.append(str(exc))
        baseline = {}
        precondition = {}
        identity = {}
        canonical = {}
        stop_sets = {}
        bucket_snap = {}
        fk_schema = []
        fk_validation = {}

    engine_audit = audit_table_engines(conn, ("juzgado_catalogo",))
    if not engine_audit["apply_enabled"]:
        errors.append(f"non-InnoDB: {engine_audit['non_transactional']}")

    try:
        _assert_admin_and_fabian(conn)
    except ApplyAbortError as exc:
        errors.append(str(exc))

    if errors:
        raise ApplyAbortError("; ".join(errors))

    return {
        "status": "PHASE2E_J_PREFLIGHT_OK",
        "baseline": baseline,
        "phase2e_r_precondition": precondition,
        "identity_revalidation": identity,
        "juzgado_audit": juzgado_audit,
        "fk_schema": fk_schema,
        "fk_validation": fk_validation,
        "canonical_juzgados": canonical,
        "classification_snapshot": bucket_snap,
        "stop_sets": stop_sets,
        "protected_juzgado_ids": sorted(protected_jz),
        "protected_closure": closure,
        "known_test_guards": test_guard,
        "oficio_1662_guard": {"exists": False},
    }


def apply_phase2e_juzgado_cleanup(
    conn: Connection,
    execution_manifest: dict[str, Any],
    protected_path: Path,
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
    diag_data: dict[str, Any] | None = None,
    phase2e_r_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aplica DELETE juzgado_catalogo id=922 en transacción única."""
    delete_ids = _load_juzgado_id(execution_manifest)
    counts_before = {
        "juzgado_catalogo": _count(conn, "juzgado_catalogo"),
        "oficio": _count(conn, "oficio"),
        **{k: _count(conn, k) for k in BASELINE_POST_2E_R},
        **{k: _count(conn, k) for k in CATALOG_PHYSICAL_POST_2E_R if k not in ("juzgado_catalogo",)},
    }

    protected_manifest = load_protected_sets(load_manifest(protected_path))

    preflight = preflight_phase2e_juzgado_apply(
        conn,
        execution_manifest,
        protected_path,
        expected_exec_hash=expected_exec_hash,
        expected_source_diag_hash=expected_source_diag_hash,
        expected_prot_hash=expected_prot_hash,
        backup_confirmed=True,
        restore_verified=restore_verified,
        manifest_paths=manifest_paths,
        diag_data=diag_data,
        phase2e_r_report=phase2e_r_report,
    )

    fk_schema = preflight["fk_schema"]
    prot = expand_protected_indirect(conn, protected_manifest)
    bucket_snap = preflight.get("classification_snapshot", {})

    if conn.in_transaction():
        conn.rollback()

    explicit_deleted: dict[str, int] = {}
    trans = conn.begin()
    try:
        result = conn.execute(
            text("DELETE FROM juzgado_catalogo WHERE id = :id"),
            {"id": JUZGADO_SAFE_ID},
        )
        explicit_deleted["juzgado_catalogo"] = result.rowcount or 0
        if explicit_deleted["juzgado_catalogo"] != 1:
            raise ApplyAbortError(f"affected_rows={explicit_deleted['juzgado_catalogo']} != 1")

        remaining = int(
            _scalar(
                conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE id = :id", {"id": JUZGADO_SAFE_ID}
            )
            or 0
        )
        if remaining != 0:
            raise ApplyAbortError("juzgado id922 still exists")

        if _count(conn, "juzgado_catalogo") != 842:
            raise ApplyAbortError(f"juzgado postcount={_count(conn, 'juzgado_catalogo')}")

        if _count(conn, "oficio") != BASELINE_POST_2E_R["oficio"]:
            raise ApplyAbortError(f"oficio changed: {_count(conn, 'oficio')}")

        canonical_post = _validate_canonical_juzgados(conn)

        for pid in PROTECTED_JUZGADO_IDS:
            if not _scalar(conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE id = :id", {"id": pid}):
                raise ApplyAbortError(f"protected juzgado {pid} missing post")

        for tbl, expected in BASELINE_POST_2E_R.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"unchanged {tbl}: {_count(conn, tbl)} != {expected}")

        if _count(conn, "relevador") != 10:
            raise ApplyAbortError("relevador != 10 post")

        _validate_stop_sets(conn)

        protected_preserved: dict[str, Any] = {}
        for entity, min_count in PROTECTED_POSTCONDITION_MIN.items():
            ids = prot.get(entity, set())
            found = _count_ids_exist(conn, entity, ids)
            protected_preserved[entity] = {"expected": len(ids), "found": found}
            if found != len(ids):
                raise ApplyAbortError(f"protected {entity}: {found} != {len(ids)}")
            if found < min_count:
                raise ApplyAbortError(f"protected min {entity}: {found} < {min_count}")

        orphans = _check_juzgado_orphans(conn, fk_schema)
        if orphans:
            raise ApplyAbortError(f"orphans: {orphans}")

        trans.commit()
        committed = True
        status = "COMMITTED"
    except Exception as exc:
        trans.rollback()
        committed = False
        status = "ROLLED_BACK"
        raise ApplyAbortError(str(exc)) from exc

    counts_after = {
        "juzgado_catalogo": _count(conn, "juzgado_catalogo"),
        "oficio": _count(conn, "oficio"),
        **{k: _count(conn, k) for k in BASELINE_POST_2E_R},
        **{k: _count(conn, k) for k in CATALOG_PHYSICAL_POST_2E_R},
    }

    return {
        "ticket": "PREDEPLOY-CLEANUP.3M.2J",
        "applied_at": datetime.now().isoformat(),
        "database": confirm_database,
        "alembic_revision": preflight["baseline"]["alembic_revision"],
        "freeze_method": freeze_method,
        "phase2e_r_precondition": {
            "committed": phase2e_r_report.get("committed") if phase2e_r_report else True,
            "relevador_count": counts_after["relevador"],
            "phase2e_r_report": phase2e_r_report.get("manifest_path") if phase2e_r_report else None,
        },
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
        "identity_revalidation": preflight["identity_revalidation"],
        "fk_schema": {"juzgado_catalogo": fk_schema},
        "fk_validation": preflight["fk_validation"],
        "explicit_deleted": {"juzgado_catalogo": 1, "ids": [JUZGADO_SAFE_ID]},
        "cascade_deleted": {"total": 0},
        "set_null_affected": {"total": 0},
        "counts_after": counts_after,
        "manifest_ids_remaining": {"juzgado_catalogo": 0},
        "canonical_juzgados_preserved": canonical_post,
        "protected_juzgados_preserved": sorted(PROTECTED_JUZGADO_IDS),
        "blocked_test_juzgados_preserved": bucket_snap,
        "indeterminate_juzgados_preserved": {"count": INDETERMINATE_JUZGADO_COUNT},
        "other_catalogs_preserved": {
            "relevador": counts_after["relevador"],
            "calle_catalogo": counts_after["calle_catalogo"],
            "rubro": counts_after["rubro"],
        },
        "stop_sets_preserved": preflight.get("stop_sets", {}),
        "protected_preserved": protected_preserved,
        "orphan_checks": orphans,
        "known_test_guards": preflight.get("known_test_guards", {}),
        "users_effect": {"users_baseline": BASELINE_POST_2E_R["users"], "users_affected": 0},
        "preflight": preflight,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "phase2e_r_executed": True,
        "phase2e_j_executed": committed,
        "phase2e_closure": {
            "2E_R": "CLOSED",
            "2E_J": "CLOSED" if committed else "PENDING",
            "2E_C": "STOP_PRESERVE",
            "2E_U": "STOP_PRESERVE",
        },
    }
