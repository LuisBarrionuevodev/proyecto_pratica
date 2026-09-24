"""
PREDEPLOY-CLEANUP.3L.1 — congelar execution manifest FASE 2D USERS (833 SAFE).
Solo lectura en DB. Sin DELETE/UPDATE/INSERT.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.manifest_io import (
    file_sha256,
    load_manifest,
    manifest_sha256,
    validate_ids_exist,
)
from app.domains.predeploy_cleanup.phase2_blockers_diag import _scalar, audit_user_blockers
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    _known_test_guard,
    _load_known_test_ids_from_manifests,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.route_residual_diag import (
    BLOCKED_NOTIF_25,
    FUTURE_EXPEDIENTE_27,
    ROUTE_IDS_12,
)
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    protection_closure_check,
)
from app.domains.predeploy_cleanup.users_phase2d_diag import (
    JUZGADO_922,
    load_all_user_foreign_keys,
)

EXPECTED_SAFE = 833
EXPECTED_BLOCKED = 1956
EXPECTED_USERS_TOTAL = 2803
EXPECTED_USERS_AFTER = 1970
EXPECTED_FK_FREE = 837
EXPECTED_FK_BLOCKED = 1966

SYSTEM_USER_IDS = frozenset({1})
REAL_USER_IDS = frozenset(
    {124, 937, 941, 942, 969, 970, 971, 1024, 1025, 1026, 1027, 4231, 5666}
)
PRESERVE_USER_IDS = SYSTEM_USER_IDS | REAL_USER_IDS

CLASSIFICATION_EXPECTED = {
    "SYSTEM_OR_ADMIN_PRESERVE": 1,
    "REAL_PROTECTED_USER": 13,
    "CONFIRMADO_TEST_FK_FREE": 833,
    "CONFIRMADO_TEST_BLOCKED": 1956,
    "INDETERMINATE_FK_FREE": 0,
    "INDETERMINATE_BLOCKED": 0,
}

BASELINE_POST_3K2 = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "ruta_trabajo": 2703,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3685,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8001,
    "actuaciones": 8074,
    "denuncia": 417,
    "relevamiento": 4566,
    "orden_trabajo": 8810,
    "notificacion": 2453,
    "comprobacion": 1529,
    "expediente": 2913,
    "oficio": 1447,
    "inspeccion": 898,
    "actuaciones_inspector": 4180,
    "acta_inspeccion_item": 52,
    "clausura": 69,
    "decomiso": 25,
    "relevamiento_relevador": 525,
    "profiles": 7,
    "password_reset_codes": 1,
}


class ManifestFreezeError(Exception):
    """Aborta freeze del manifest FASE 2D USERS."""


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    if db != "digitaliza_sandbox":
        raise ManifestFreezeError(f"DATABASE()={db}")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    if alembic != "l7m8n9o0p1q2":
        raise ManifestFreezeError(f"alembic={alembic}")
    counts: dict[str, int] = {}
    drift: list[str] = []
    for table, expected in BASELINE_POST_3K2.items():
        actual = int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)
        counts[table] = actual
        if actual != expected:
            drift.append(f"{table}: {actual} != {expected}")
    if drift:
        raise ManifestFreezeError(f"baseline drift: {drift}")
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "baseline_ok": True,
        "drift": [],
    }


def load_diag_for_freeze(diag_path: Path) -> dict[str, Any]:
    """Carga y valida diagnóstico 3L sin regenerar."""
    data = json.loads(diag_path.read_text(encoding="utf-8"))
    if data.get("writes_executed") is not False:
        raise ManifestFreezeError("source diag writes_executed != false")
    if data.get("users_total") != EXPECTED_USERS_TOTAL:
        raise ManifestFreezeError(f"users_total={data.get('users_total')}")
    if data["fk_free_users"]["count"] != EXPECTED_FK_FREE:
        raise ManifestFreezeError(f"fk_free={data['fk_free_users']['count']}")
    if data["fk_blocked_users"]["count"] != EXPECTED_FK_BLOCKED:
        raise ManifestFreezeError(f"fk_blocked={data['fk_blocked_users']['count']}")

    summary = data.get("classification_summary", {})
    for key, expected in CLASSIFICATION_EXPECTED.items():
        if summary.get(key) != expected:
            raise ManifestFreezeError(f"classification {key}: {summary.get(key)} != {expected}")
    if sum(summary.values()) != EXPECTED_USERS_TOTAL:
        raise ManifestFreezeError("classification sum != 2803")

    safe_ids = data["safe_users"]["SAFE_USERS_2D"]
    if len(safe_ids) != EXPECTED_SAFE:
        raise ManifestFreezeError(f"SAFE count={len(safe_ids)}")
    if len(safe_ids) != len(set(safe_ids)):
        raise ManifestFreezeError("SAFE duplicate IDs")

    if data["safe_users"].get("active_true") != EXPECTED_SAFE:
        raise ManifestFreezeError("active_true safe mismatch")
    if data["safe_users"].get("active_false", 0) != 0:
        raise ManifestFreezeError("active_false safe != 0")

    return data


def _identity_fingerprint(row: dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "id": row["id"],
            "username": row.get("username"),
            "email": row.get("email"),
            "role": row.get("role"),
            "is_active": bool(row.get("is_active")),
            "created_at": str(row.get("created_at")),
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_identity_snapshot(conn: Connection, safe_ids: list[int]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for chunk in _chunk_ids(set(safe_ids), 400):
        ph = ",".join(str(i) for i in chunk)
        for row in _rows(
            conn,
            f"""
            SELECT id, username, email, role, is_active, created_at
            FROM users WHERE id IN ({ph}) ORDER BY id
            """,
        ):
            fp = _identity_fingerprint(row)
            prov = row.copy()
            prov["classification"] = "CONFIRMADO_TEST_FK_FREE"
            prov["test_provenance_conclusive"] = True
            prov["whitelist"] = False
            prov["system_admin_preserve"] = False
            prov["identity_fingerprint"] = fp
            rows.append(prov)

    rows.sort(key=lambda r: r["id"])
    if len(rows) != EXPECTED_SAFE:
        raise ManifestFreezeError(f"identity snapshot rows={len(rows)}")

    aggregate = hashlib.sha256(
        json.dumps(
            [{"id": r["id"], "fingerprint": r["identity_fingerprint"]} for r in rows],
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    active_true = sum(1 for r in rows if r.get("is_active"))
    return {
        "rows": rows,
        "count": len(rows),
        "identity_snapshot_hash": aggregate,
        "active_true": active_true,
        "active_false": len(rows) - active_true,
    }


def _validate_user1(conn: Connection) -> dict[str, Any]:
    row = _rows(
        conn,
        "SELECT id, username, email, role, is_active FROM users WHERE id = 1 LIMIT 1",
    )
    if not row:
        raise ManifestFreezeError("user id=1 missing")
    u = row[0]
    if (u.get("username") or "").lower() != "admin":
        raise ManifestFreezeError(f"user1 username={u.get('username')}")
    if (u.get("email") or "").lower() != "admin@local":
        raise ManifestFreezeError(f"user1 email={u.get('email')}")

    fk_edges = load_all_user_foreign_keys(conn)
    refs = 0
    by_table: list[dict[str, Any]] = []
    for edge in fk_edges:
        tbl = edge["child_table"]
        col = edge["child_column"]
        cnt = int(_scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = 1") or 0)
        if cnt:
            by_table.append({"table": tbl, "column": col, "refs": cnt})
            refs += cnt

    return {
        "user_id": 1,
        "username": u.get("username"),
        "email": u.get("email"),
        "classification": "SYSTEM_OR_ADMIN_PRESERVE",
        "physical_refs_current": refs,
        "by_table": sorted(by_table, key=lambda x: -x["refs"]),
        "no_delete": True,
    }


def _validate_safe_fk_refs(
    conn: Connection, safe_ids: set[int], fk_edges: list[dict[str, Any]]
) -> dict[str, Any]:
    """Revalida físicamente 0 refs para SAFE en todas las FK edges."""
    by_edge: list[dict[str, Any]] = []
    restrict_total = 0
    cascade_total = 0
    set_null_total = 0

    for edge in fk_edges:
        tbl = edge["child_table"]
        col = edge["child_column"]
        rule = edge["delete_rule"]
        cnt = 0
        for chunk in _chunk_ids(safe_ids, 400):
            ph = ",".join(str(i) for i in chunk)
            cnt += int(
                _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` IN ({ph})") or 0
            )
        if cnt:
            raise ManifestFreezeError(f"SAFE refs on {tbl}.{col}: {cnt}")
        by_edge.append(
            {
                "child_table": tbl,
                "child_column": col,
                "delete_rule": rule,
                "update_rule": edge["update_rule"],
                "safe_refs": 0,
            }
        )
        if rule == "RESTRICT":
            restrict_total += cnt
        elif rule == "CASCADE":
            cascade_total += cnt
        elif rule == "SET NULL":
            set_null_total += cnt

    profiles_safe = 0
    prc_safe = 0
    for chunk in _chunk_ids(safe_ids, 400):
        ph = ",".join(str(i) for i in chunk)
        profiles_safe += int(
            _scalar(conn, f"SELECT COUNT(*) FROM profiles WHERE user_id IN ({ph})") or 0
        )
        prc_safe += int(
            _scalar(
                conn, f"SELECT COUNT(*) FROM password_reset_codes WHERE user_id IN ({ph})"
            )
            or 0
        )
    if profiles_safe or prc_safe:
        raise ManifestFreezeError(
            f"auth children on SAFE: profiles={profiles_safe} prc={prc_safe}"
        )

    return {
        "safe_users_count": len(safe_ids),
        "edges_revalidated": len(by_edge),
        "total_refs": 0,
        "restrict_refs": restrict_total,
        "cascade_refs": cascade_total,
        "set_null_refs": set_null_total,
        "profiles_safe_refs": profiles_safe,
        "password_reset_codes_safe_refs": prc_safe,
        "by_edge": by_edge,
        "valid": True,
    }


def _derive_blocked_test_ids(conn: Connection, safe_ids: set[int]) -> set[int]:
    """IDs CONFIRMADO_TEST_BLOCKED = todos los users - SAFE - preserve."""
    all_ids = _fetch_ids(conn, "SELECT id FROM users")
    blocked = all_ids - safe_ids - PRESERVE_USER_IDS
    if len(blocked) != EXPECTED_BLOCKED:
        raise ManifestFreezeError(f"blocked derived count={len(blocked)}")
    pattern_test = _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")
    if not blocked.issubset(pattern_test):
        extra = sorted(blocked - pattern_test)[:10]
        raise ManifestFreezeError(f"blocked not all test pattern: {extra}")
    if blocked & safe_ids:
        raise ManifestFreezeError("safe ∩ blocked != 0")
    if blocked & PRESERVE_USER_IDS:
        raise ManifestFreezeError("blocked ∩ preserve != 0")
    return blocked


def _validate_preserve_intersections(safe_ids: set[int]) -> None:
    if safe_ids & PRESERVE_USER_IDS:
        raise ManifestFreezeError("SAFE ∩ PRESERVE != 0")
    if 1 in safe_ids:
        raise ManifestFreezeError("user 1 in SAFE")


def _route_residual_guard(conn: Connection) -> dict[str, Any]:
    remaining = 0
    for rtid in ROUTE_IDS_12:
        if _scalar(conn, "SELECT COUNT(*) FROM ruta_trabajo WHERE id = :id", {"id": rtid}):
            remaining += 1
    return {
        "route_ids_12": list(ROUTE_IDS_12),
        "route_residual_safe_remaining": remaining,
        "guard_ok": remaining == 0,
    }


def _admin_graph_guard(conn: Connection) -> dict[str, Any]:
    notif_remain = 0
    for nid in BLOCKED_NOTIF_25:
        if _scalar(conn, "SELECT COUNT(*) FROM notificacion WHERE id = :id", {"id": nid}):
            notif_remain += 1
    exp_remain = 0
    for eid in FUTURE_EXPEDIENTE_27:
        if _scalar(conn, "SELECT COUNT(*) FROM expediente WHERE id = :id", {"id": eid}):
            exp_remain += 1
    comp_2289 = bool(_scalar(conn, "SELECT COUNT(*) FROM comprobacion WHERE id = 2289"))
    oficio_1662 = bool(_scalar(conn, "SELECT COUNT(*) FROM oficio WHERE id = 1662"))
    total = notif_remain + exp_remain + int(comp_2289) + int(oficio_1662)
    return {
        "admin_graph_safe_remaining": total,
        "notificaciones_remaining": notif_remain,
        "expedientes_remaining": exp_remain,
        "comprobacion_2289_remaining": comp_2289,
        "oficio_1662_remaining": oficio_1662,
        "guard_ok": total == 0,
    }


def _juzgado_922_guard(conn: Connection) -> dict[str, Any]:
    exists = bool(
        _scalar(conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE id = :jz", {"jz": JUZGADO_922})
    )
    refs = int(
        _scalar(conn, "SELECT COUNT(*) FROM oficio WHERE juzgado_id = :jz", {"jz": JUZGADO_922})
        or 0
    )
    if not exists:
        raise ManifestFreezeError("juzgado 922 missing")
    if refs != 0:
        raise ManifestFreezeError(f"juzgado 922 refs={refs}")
    return {
        "juzgado_id": JUZGADO_922,
        "exists": exists,
        "fk_refs_current": refs,
        "status": "READY_FOR_PHASE2E",
        "no_delete_in_2d": True,
    }


def _uniqueness_audit(conn: Connection) -> dict[str, Any]:
    return {
        "username_unique_violations": int(
            _scalar(conn, "SELECT COUNT(*) - COUNT(DISTINCT username) FROM users") or 0
        ),
        "email_unique_violations": int(
            _scalar(conn, "SELECT COUNT(*) - COUNT(DISTINCT email) FROM users") or 0
        ),
        "identity_by_primary_key": True,
        "note": "liberar UNIQUE no es motivo del cleanup",
    }


def run_users_phase2d_manifest_freeze(
    conn: Connection,
    *,
    diag_path: Path,
    protected_path: Path,
    manifest_paths: list[Path],
) -> dict[str, Any]:
    """Orquestador freeze manifest FASE 2D USERS."""
    baseline = _baseline_check(conn)
    diag_data = load_diag_for_freeze(diag_path)
    source_diag_sha = file_sha256(diag_path)

    safe_ids_list = list(diag_data["safe_users"]["SAFE_USERS_2D"])
    safe_ids = set(safe_ids_list)

    stale = validate_ids_exist(conn, "users", safe_ids, label="users")
    if stale:
        raise ManifestFreezeError(f"missing safe users: {stale[:5]}")

    _validate_preserve_intersections(safe_ids)
    blocked_ids = _derive_blocked_test_ids(conn, safe_ids)

    fk_edges = load_all_user_foreign_keys(conn)
    fk_validation = _validate_safe_fk_refs(conn, safe_ids, fk_edges)

    identity = _build_identity_snapshot(conn, safe_ids_list)
    user1 = _validate_user1(conn)

    if user1["user_id"] in safe_ids:
        raise ManifestFreezeError("user 1 in safe set")

    whitelist_diag_ids = {w["id"] for w in diag_data.get("real_user_whitelist", [])}
    if REAL_USER_IDS | {1} != whitelist_diag_ids:
        missing = (REAL_USER_IDS | {1}) - whitelist_diag_ids
        extra = whitelist_diag_ids - REAL_USER_IDS - {1}
        if missing or extra:
            raise ManifestFreezeError(f"whitelist drift missing={missing} extra={extra}")

    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))
    virtual = VirtualDeleteState()
    virtual.add_explicit("users", safe_ids)
    closure = protection_closure_check(virtual, prot)
    if not closure.get("valid"):
        raise ManifestFreezeError(f"protected closure: {closure.get('conflicts', [])[:3]}")

    known = _load_known_test_ids_from_manifests(manifest_paths)
    test_guard = _known_test_guard(conn, known)
    if not test_guard["guard_ok"]:
        raise ManifestFreezeError("known test act/ot guard failed")

    route_guard = _route_residual_guard(conn)
    if not route_guard["guard_ok"]:
        raise ManifestFreezeError(f"route residual remaining={route_guard['route_residual_safe_remaining']}")

    admin_guard = _admin_graph_guard(conn)
    if not admin_guard["guard_ok"]:
        raise ManifestFreezeError(f"admin graph remaining={admin_guard['admin_graph_safe_remaining']}")

    juzgado_guard = _juzgado_922_guard(conn)
    blocker_audit = audit_user_blockers(conn, blocked_ids)

    counts_before = baseline["counts"]
    counts_after = dict(counts_before)
    counts_after["users"] = EXPECTED_USERS_AFTER

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "phase": "2D_USERS",
        "phase_name": "confirmado_test_fk_free_users",
        "mode": "EXECUTION_MANIFEST_FROZEN",
        "writes_executed": False,
        "database": baseline["database"],
        "alembic_revision": baseline["alembic_revision"],
        "source_diag_path": str(diag_path.resolve()),
        "source_diag_sha256": source_diag_sha,
        "protected_manifest_path": str(protected_path.resolve()),
        "protected_manifest_sha256": file_sha256(protected_path),
        "users_total_before": EXPECTED_USERS_TOTAL,
        "classification": {
            "safe_confirmado_test_fk_free": EXPECTED_SAFE,
            "summary": CLASSIFICATION_EXPECTED,
        },
        "entities": {
            "users": sorted(safe_ids),
        },
        "identity_snapshot": identity["rows"],
        "identity_snapshot_hash": identity["identity_snapshot_hash"],
        "preserve": {
            "system_user_ids": sorted(SYSTEM_USER_IDS),
            "real_user_ids": sorted(REAL_USER_IDS),
            "blocked_test_user_ids": sorted(blocked_ids),
            "policy": (
                "NO_DELETE blocked_test, real, system; "
                "NO operational cleanup to free users; "
                "NO UPDATE created_by; NO SET NULL manual"
            ),
        },
        "fk_schema": {
            "ALL_USER_FOREIGN_KEYS": fk_edges,
            "edge_count": len(fk_edges),
        },
        "fk_validation": fk_validation,
        "expected_effects": {
            "explicit_delete_users": EXPECTED_SAFE,
            "cascade": 0,
            "set_null": 0,
            "restrict": 0,
        },
        "expected_counts_before": counts_before,
        "expected_counts_after": counts_after,
        "expected_users_after": EXPECTED_USERS_AFTER,
        "survivor_reconciliation": {
            "blocked_test": EXPECTED_BLOCKED,
            "real": len(REAL_USER_IDS),
            "system": len(SYSTEM_USER_IDS),
            "total": EXPECTED_USERS_AFTER,
            "formula": "1956 + 13 + 1 = 1970",
        },
        "active_status_safe": {
            "active_true": identity["active_true"],
            "active_false": identity["active_false"],
        },
        "user1_guard": user1,
        "audit_fallback_metadata": {
            "ticket": "AUDIT-CREATED-BY-FALLBACK-PREDEPLOY",
            "user_id": 1,
            "physical_refs_current": user1["physical_refs_current"],
            "no_fix_in_2d": True,
        },
        "blocker_snapshot": {
            "blocked_test_users_count": EXPECTED_BLOCKED,
            "blocker_distribution": blocker_audit.get("blocker_table", []),
        },
        "protected_intersection": 0,
        "protected_closure_detail": closure,
        "known_test_operational_guards": {
            "known_test_acts_remaining": test_guard["known_test_act_ids_remaining_count"],
            "known_test_ot_remaining": test_guard["known_test_ot_ids_remaining_count"],
            "route_residual_safe_remaining": route_guard["route_residual_safe_remaining"],
            "admin_graph_safe_remaining": admin_guard["admin_graph_safe_remaining"],
            "guard_ok": (
                test_guard["guard_ok"]
                and route_guard["guard_ok"]
                and admin_guard["guard_ok"]
            ),
            "detail": {
                "known_test": test_guard,
                "route_residual": route_guard,
                "admin_graph": admin_guard,
            },
        },
        "juzgado_922_guard": juzgado_guard,
        "users_uniqueness": _uniqueness_audit(conn),
        "unchanged_operational_tables": {
            k: v for k, v in counts_before.items() if k not in ("users", "profiles", "password_reset_codes")
        },
        "validation": {
            "safe_count": EXPECTED_SAFE,
            "safe_ids_exist": len(stale) == 0,
            "no_duplicates": len(safe_ids) == len(safe_ids_list),
            "fk_refs_zero": fk_validation["valid"],
            "auth_children_zero": True,
            "preserve_disjoint": True,
        },
        "document_cleanup_policy": (
            "DELETE only CONFIRMADO_TEST_FK_FREE users (833). "
            "Never delete operational data to free users."
        ),
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)

    return {
        "ticket": "PREDEPLOY-CLEANUP.3L.1",
        "writes_executed": False,
        "baseline": baseline,
        "source_diag_sha256": source_diag_sha,
        "classification_summary": CLASSIFICATION_EXPECTED,
        "safe_users_count": EXPECTED_SAFE,
        "safe_users_ids": sorted(safe_ids),
        "preserve_counts": {
            "system": len(SYSTEM_USER_IDS),
            "real": len(REAL_USER_IDS),
            "blocked_test": len(blocked_ids),
            "preserve_total_non_test": len(PRESERVE_USER_IDS),
        },
        "fk_schema": manifest["fk_schema"],
        "fk_validation": fk_validation,
        "identity_snapshot_hash": identity["identity_snapshot_hash"],
        "expected_effects": manifest["expected_effects"],
        "expected_postcounts": {
            "users_before": EXPECTED_USERS_TOTAL,
            "users_after": EXPECTED_USERS_AFTER,
            "profiles": counts_before["profiles"],
            "password_reset_codes": counts_before["password_reset_codes"],
        },
        "protected_guard": {
            "protected_intersection": 0,
            "closure_valid": closure.get("valid"),
        },
        "known_test_guards": manifest["known_test_operational_guards"],
        "juzgado_922_guard": juzgado_guard,
        "manifest": manifest,
        "manifest_sha256": manifest["manifest_sha256"],
    }


def write_freeze_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
