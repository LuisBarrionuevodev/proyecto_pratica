"""Aplicación FASE 2E-R: DELETE relevador id=2 (transacción única)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.catalogos.canonical.normalize import normalize_catalog_key
from app.domains.catalogos.canonical.relevadores import RELEVADORES_CANONICOS
from app.domains.predeploy_cleanup.apply_service import (
    ApplyAbortError,
    _assert_admin_and_fabian,
    _count_ids_exist,
    audit_table_engines,
)
from app.domains.predeploy_cleanup.catalogs_phase2e_manifest_freeze import (
    BASELINE_POST_3L2,
    CATALOG_PHYSICAL_BASELINE,
    EXPECTED_RELEVADOR_NOMBRE,
    JUZGADO_SAFE_ID,
    RELEVADOR_PROVENANCE,
    RELEVADOR_SAFE_ID,
    _baseline_check,
    _incoming_fk_schema,
    _operational_guards,
    _protected_closure_check,
    _refs_for_parent_id,
    _validate_relevador_id2,
)
from app.domains.predeploy_cleanup.manifest_io import (
    entity_ids,
    load_manifest,
    manifest_sha256,
    validate_ids_exist,
)
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets

EXPECTED_EXEC_HASH = "f5c4babd6aeaae73d848de25aaab62329769538e5527b782d7dcf9880d5b62f4"
EXPECTED_SOURCE_DIAG_HASH = "d9beb74d93d0280163523b851785e68a2c8307bdfc018f46018027652c5fa4e7"
EXPECTED_PROT_HASH = "d8a1fda3a10e46dcdb90b22038d73e1e08c76754a59c96dc11cff4377a3b102e"

CANONICAL_SURVIVOR_IDS = frozenset({1, 4, 5, 6, 7, 8, 9, 10, 11, 12})
RELEVADOR_CANONICAL_KEYS = frozenset(normalize_catalog_key(n) for n in RELEVADORES_CANONICOS)

UNCHANGED_OPERATIVE = dict(BASELINE_POST_3L2)
OTHER_CATALOGS_BEFORE = {
    "juzgado_catalogo": CATALOG_PHYSICAL_BASELINE["juzgado_catalogo"],
    "calle_catalogo": CATALOG_PHYSICAL_BASELINE["calle_catalogo"],
    "rubro": CATALOG_PHYSICAL_BASELINE["rubro"],
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


def _count(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _load_relevador_id(execution_manifest: dict[str, Any]) -> set[int]:
    ids = entity_ids(execution_manifest, "relevador")
    if ids != {RELEVADOR_SAFE_ID}:
        raise ApplyAbortError(f"relevador entities {ids} != {{{RELEVADOR_SAFE_ID}}}")
    frozen = set(execution_manifest.get("entities", {}).get("relevador", []))
    if frozen != ids:
        raise ApplyAbortError("entity_ids != manifest entities.relevador")
    return ids


def _validate_identity_snapshot(execution_manifest: dict[str, Any]) -> dict[str, Any]:
    snap = execution_manifest.get("identity_snapshot", [])
    if len(snap) != 1 or snap[0]["id"] != RELEVADOR_SAFE_ID:
        raise ApplyAbortError("identity_snapshot invalid")
    row = snap[0]
    if row.get("nombre") != EXPECTED_RELEVADOR_NOMBRE:
        raise ApplyAbortError(f"identity nombre={row.get('nombre')}")
    if row.get("classification") != "CONFIRMADO_TEST_FK_FREE":
        raise ApplyAbortError("identity classification mismatch")
    prov = set(row.get("provenance") or [])
    if prov != set(RELEVADOR_PROVENANCE):
        raise ApplyAbortError(f"identity provenance={prov}")
    return row


def _validate_canonical_present(conn: Connection) -> dict[str, Any]:
    rows = _rows(conn, "SELECT id, nombre FROM relevador ORDER BY id")
    canonical_ids = [
        r["id"]
        for r in rows
        if normalize_catalog_key(r.get("nombre") or "") in RELEVADOR_CANONICAL_KEYS
    ]
    if len(canonical_ids) != 10:
        raise ApplyAbortError(f"canonical count={len(canonical_ids)}")
    if set(canonical_ids) != CANONICAL_SURVIVOR_IDS:
        raise ApplyAbortError(f"canonical ids={canonical_ids}")
    if RELEVADOR_SAFE_ID in canonical_ids:
        raise ApplyAbortError("id2 in canonical set")
    fabian = next((r for r in rows if r["id"] == 1), None)
    if not fabian or fabian.get("nombre") != "Fabian Esquivel":
        raise ApplyAbortError("id1 Fabian missing")
    return {
        "canonical_ids": sorted(canonical_ids),
        "canonical_count": 10,
        "fabian_id": 1,
        "fabian_nombre": fabian.get("nombre"),
    }


def _juzgado_922_guard(conn: Connection) -> dict[str, Any]:
    exists = bool(
        _scalar(conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE id = :id", {"id": JUZGADO_SAFE_ID})
    )
    refs = int(
        _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE juzgado_id = :id", {"id": JUZGADO_SAFE_ID}) or 0
    )
    if not exists:
        raise ApplyAbortError("juzgado 922 missing")
    if refs != 0:
        raise ApplyAbortError(f"juzgado 922 refs={refs}")
    return {"juzgado_id": JUZGADO_SAFE_ID, "exists": True, "fk_refs": 0, "ready_for_2e_j": True}


def _other_catalogs_guard(conn: Connection) -> dict[str, Any]:
    counts = {k: _count(conn, k) for k in OTHER_CATALOGS_BEFORE}
    for k, expected in OTHER_CATALOGS_BEFORE.items():
        if counts[k] != expected:
            raise ApplyAbortError(f"{k}={counts[k]} != {expected}")
    jz922 = _juzgado_922_guard(conn)
    return {"counts": counts, "juzgado_922": jz922}


def _check_relevador_orphans(conn: Connection, fk_schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
    orphans: list[dict[str, Any]] = []
    for edge in fk_schema:
        tbl = edge["child_table"]
        col = edge["child_column"]
        cnt = int(
            _scalar(
                conn,
                f"""
                SELECT COUNT(*) FROM `{tbl}` c
                LEFT JOIN relevador r ON c.`{col}` = r.id
                WHERE c.`{col}` IS NOT NULL AND r.id IS NULL
                """,
            )
            or 0
        )
        if cnt:
            orphans.append({"child_table": tbl, "child_column": col, "orphan_count": cnt})
    return orphans


def preflight_phase2e_relevador_apply(
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
) -> dict[str, Any]:
    """Preflight 2E-R antes de BEGIN."""
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

    closure: dict[str, Any] = {}
    test_guard: dict[str, Any] = {}
    relevador_audit: dict[str, Any] = {}
    identity: dict[str, Any] = {}
    canonical: dict[str, Any] = {}
    other_catalogs: dict[str, Any] = {}

    try:
        baseline = _baseline_check(conn)
        delete_ids = _load_relevador_id(execution_manifest)
        identity = _validate_identity_snapshot(execution_manifest)

        stale = validate_ids_exist(conn, "relevador", delete_ids, label="relevador")
        if stale:
            errors.append(f"missing relevador: {stale}")

        if diag_data is None:
            errors.append("diag_data required")
        else:
            relevador_audit = _validate_relevador_id2(conn, diag_data)

        fk_schema = _incoming_fk_schema(conn, "relevador")
        fk_validation = _refs_for_parent_id(conn, "relevador", RELEVADOR_SAFE_ID, fk_schema)
        if not fk_validation["valid_fk_free"]:
            errors.append(f"id2 FK refs: {fk_validation}")

        canonical = _validate_canonical_present(conn)
        other_catalogs = _other_catalogs_guard(conn)

        closure = _protected_closure_check(conn, protected_path, "relevador", delete_ids)

        if manifest_paths:
            test_guard = _operational_guards(conn, manifest_paths)

    except Exception as exc:
        errors.append(str(exc))
        baseline = {}

    engine_audit = audit_table_engines(conn, ("relevador",))
    if not engine_audit["apply_enabled"]:
        errors.append(f"non-InnoDB: {engine_audit['non_transactional']}")

    try:
        _assert_admin_and_fabian(conn)
    except ApplyAbortError as exc:
        errors.append(str(exc))

    if errors:
        raise ApplyAbortError("; ".join(errors))

    return {
        "status": "PHASE2E_R_PREFLIGHT_OK",
        "baseline": baseline,
        "identity_revalidation": identity,
        "relevador_audit": relevador_audit,
        "fk_schema": fk_schema,
        "fk_validation": fk_validation,
        "canonical_relevadores": canonical,
        "other_catalogs": other_catalogs,
        "protected_closure": closure,
        "known_test_guards": test_guard,
    }


def apply_phase2e_relevador_cleanup(
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
) -> dict[str, Any]:
    """Aplica DELETE relevador id=2 en transacción única."""
    delete_ids = _load_relevador_id(execution_manifest)
    counts_before = {
        "relevador": _count(conn, "relevador"),
        "relevamiento_relevador": _count(conn, "relevamiento_relevador"),
        **{k: _count(conn, k) for k in UNCHANGED_OPERATIVE},
        **{k: _count(conn, k) for k in OTHER_CATALOGS_BEFORE},
    }

    protected_manifest = load_protected_sets(load_manifest(protected_path))

    preflight = preflight_phase2e_relevador_apply(
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
    )

    fk_schema = preflight["fk_schema"]
    rr_before = counts_before["relevamiento_relevador"]
    prot = expand_protected_indirect(conn, protected_manifest)

    if conn.in_transaction():
        conn.rollback()

    explicit_deleted: dict[str, int] = {}
    trans = conn.begin()
    try:
        result = conn.execute(
            text("DELETE FROM relevador WHERE id = :id"),
            {"id": RELEVADOR_SAFE_ID},
        )
        explicit_deleted["relevador"] = result.rowcount or 0
        if explicit_deleted["relevador"] != 1:
            raise ApplyAbortError(f"affected_rows={explicit_deleted['relevador']} != 1")

        remaining = int(
            _scalar(conn, "SELECT COUNT(*) FROM relevador WHERE id = :id", {"id": RELEVADOR_SAFE_ID}) or 0
        )
        if remaining != 0:
            raise ApplyAbortError("relevador id2 still exists")

        rr_after = _count(conn, "relevamiento_relevador")
        if rr_after != rr_before:
            raise ApplyAbortError(f"relevamiento_relevador changed {rr_before}->{rr_after}")

        if _count(conn, "relevador") != 10:
            raise ApplyAbortError(f"relevador postcount={_count(conn, 'relevador')}")

        canonical_post = _validate_canonical_present(conn)
        fabian_refs = int(
            _scalar(conn, "SELECT COUNT(*) FROM relevamiento_relevador WHERE relevador_id = 1") or 0
        )
        if fabian_refs != 525:
            raise ApplyAbortError(f"fabian refs={fabian_refs}")

        for tbl, expected in UNCHANGED_OPERATIVE.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"unchanged {tbl}: {_count(conn, tbl)} != {expected}")

        for tbl, expected in OTHER_CATALOGS_BEFORE.items():
            if _count(conn, tbl) != expected:
                raise ApplyAbortError(f"catalog {tbl}: {_count(conn, tbl)} != {expected}")

        jz922 = _juzgado_922_guard(conn)

        protected_preserved: dict[str, Any] = {}
        for entity, min_count in PROTECTED_POSTCONDITION_MIN.items():
            ids = prot.get(entity, set())
            found = _count_ids_exist(conn, entity, ids)
            protected_preserved[entity] = {"expected": len(ids), "found": found}
            if found != len(ids):
                raise ApplyAbortError(f"protected {entity}: {found} != {len(ids)}")
            if found < min_count:
                raise ApplyAbortError(f"protected min {entity}: {found} < {min_count}")

        orphans = _check_relevador_orphans(conn, fk_schema)
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
        "relevador": _count(conn, "relevador"),
        "relevamiento_relevador": _count(conn, "relevamiento_relevador"),
        **{k: _count(conn, k) for k in UNCHANGED_OPERATIVE},
        **{k: _count(conn, k) for k in OTHER_CATALOGS_BEFORE},
    }

    return {
        "ticket": "PREDEPLOY-CLEANUP.3M.2R",
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
        "identity_revalidation": preflight["identity_revalidation"],
        "fk_schema": {"relevador": fk_schema},
        "fk_validation": preflight["fk_validation"],
        "explicit_deleted": {"relevador": 1, "ids": [RELEVADOR_SAFE_ID]},
        "cascade_deleted": {"total": 0},
        "set_null_affected": {"total": 0},
        "counts_after": counts_after,
        "manifest_ids_remaining": {"relevador": 0},
        "canonical_relevadores_preserved": canonical_post,
        "fabian_guard": {
            "id": 1,
            "nombre": "Fabian Esquivel",
            "relevamiento_relevador_refs": fabian_refs,
        },
        "other_catalogs_preserved": {
            "counts": {k: counts_after[k] for k in OTHER_CATALOGS_BEFORE},
            "juzgado_922": jz922,
        },
        "juzgado_922_guard": jz922,
        "protected_preserved": protected_preserved,
        "orphan_checks": orphans,
        "known_test_guards": preflight.get("known_test_guards", {}),
        "users_effect": {"users_baseline": BASELINE_POST_3L2["users"], "users_affected": 0},
        "preflight": preflight,
        "transaction_status": status,
        "committed": committed,
        "writes_executed": committed,
        "phase2e_r_executed": committed,
        "phase2e_j_executed": False,
        "phase2e_j_precondition": {
            "phase2e_r_applied": committed,
            "relevador_count": counts_after["relevador"],
            "juzgado_catalogo": counts_after["juzgado_catalogo"],
            "note": "2E-J NOT executed in this run",
        },
    }
