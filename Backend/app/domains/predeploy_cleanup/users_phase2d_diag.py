"""
PREDEPLOY-CLEANUP.3L-DIAG — FASE 2D USERS auditoría post-cleanup.

Recalcula universo de users desde cero (FK schema, clasificación, SAFE set).
Solo SELECT. Sin DELETE/UPDATE/INSERT.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.domains.predeploy_cleanup.constants import SQL_TEST_USER_WHERE
from app.domains.predeploy_cleanup.manifest_io import load_manifest
from app.domains.predeploy_cleanup.phase2_blockers_diag import audit_user_blockers
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    _known_test_guard,
    _load_known_test_ids_from_manifests,
)
from app.domains.predeploy_cleanup.protected import expand_protected_indirect, load_protected_sets
from app.domains.predeploy_cleanup.sequential_simulator import (
    VirtualDeleteState,
    _chunk_ids,
    _fetch_ids,
    protection_closure_check,
)

JUZGADO_922 = 922
USERS_FK_FREE_ORIENTATIVE = 833

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
}

CLASSIFICATION_BUCKETS = (
    "SYSTEM_OR_ADMIN_PRESERVE",
    "REAL_PROTECTED_USER",
    "CONFIRMADO_TEST_FK_FREE",
    "CONFIRMADO_TEST_BLOCKED",
    "INDETERMINATE_FK_FREE",
    "INDETERMINATE_BLOCKED",
)

AUTH_CHILD_TABLES = (
    ("profiles", "user_id", "CASCADE"),
    ("password_reset_codes", "user_id", "CASCADE"),
)

TEST_FILE_GLOB = ("tests/**/*.py", "tests/**/*.py")
USER_ID_IN_TEST_RE = re.compile(
    r"(?:user_id|created_by_user_id|usuario_id|ejecutado_por_user_id)\s*[=:]\s*(\d+)",
    re.IGNORECASE,
)


def _scalar(conn: Connection, sql: str, params: dict | None = None) -> Any:
    row = conn.execute(text(sql), params or {}).fetchone()
    return row[0] if row else None


def _rows(conn: Connection, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def _count(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _baseline_check(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    counts = {t: _count(conn, t) for t in BASELINE_POST_3K2}
    drift = [f"{t}: {counts[t]} != {e}" for t, e in BASELINE_POST_3K2.items() if counts[t] != e]
    return {
        "database": db,
        "alembic_revision": alembic,
        "alembic_expected": "l7m8n9o0p1q2",
        "counts": counts,
        "baseline_ok": db == "digitaliza_sandbox" and alembic == "l7m8n9o0p1q2" and not drift,
        "drift": drift,
        "users_fk_free_orientative_post_3k2": USERS_FK_FREE_ORIENTATIVE,
    }


def load_all_user_foreign_keys(conn: Connection) -> list[dict[str, Any]]:
    """ALL_USER_FOREIGN_KEYS desde INFORMATION_SCHEMA + conteos físicos."""
    edges = _rows(
        conn,
        """
        SELECT
            kcu.TABLE_NAME AS child_table,
            kcu.COLUMN_NAME AS child_column,
            kcu.CONSTRAINT_NAME AS constraint_name,
            rc.DELETE_RULE AS delete_rule,
            rc.UPDATE_RULE AS update_rule
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND kcu.REFERENCED_TABLE_NAME = 'users'
          AND kcu.REFERENCED_COLUMN_NAME = 'id'
        ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME
        """,
    )
    for edge in edges:
        tbl = edge["child_table"]
        col = edge["child_column"]
        edge["physical_refs"] = int(
            _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` IS NOT NULL") or 0
        )
        edge["distinct_users"] = int(
            _scalar(conn, f"SELECT COUNT(DISTINCT `{col}`) FROM `{tbl}` WHERE `{col}` IS NOT NULL")
            or 0
        )
    return edges


def _load_all_users(conn: Connection) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT id, username, email, role, is_active, created_at, updated_at
        FROM users
        ORDER BY id
        """,
    )


def _compute_user_ref_map(
    conn: Connection, fk_edges: list[dict[str, Any]]
) -> dict[int, dict[str, Any]]:
    """Mapa user_id -> refs por tabla/columna."""
    per_user: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"ref_count_total": 0, "refs_by_table": {}, "refs_detail": []}
    )
    for edge in fk_edges:
        tbl = edge["child_table"]
        col = edge["child_column"]
        rows = _rows(
            conn,
            f"""
            SELECT `{col}` AS user_id, COUNT(*) AS cnt
            FROM `{tbl}`
            WHERE `{col}` IS NOT NULL
            GROUP BY `{col}`
            """,
        )
        for row in rows:
            uid = int(row["user_id"])
            cnt = int(row["cnt"])
            per_user[uid]["ref_count_total"] += cnt
            key = f"{tbl}.{col}"
            per_user[uid]["refs_by_table"][key] = per_user[uid]["refs_by_table"].get(key, 0) + cnt
            if len(per_user[uid]["refs_detail"]) < 30:
                per_user[uid]["refs_detail"].append(
                    {
                        "table": tbl,
                        "column": col,
                        "delete_rule": edge["delete_rule"],
                        "count": cnt,
                    }
                )
    return dict(per_user)


def _pattern_test_user_ids(conn: Connection) -> set[int]:
    return _fetch_ids(conn, f"SELECT id FROM users u WHERE {SQL_TEST_USER_WHERE}")


def _scan_test_fixture_user_ids(backend_root: Path) -> dict[str, Any]:
    """IDs literales en tests + evidencia de patrones de email en código."""
    literal_ids: set[int] = set()
    pattern_hits: list[dict[str, str]] = []
    tests_dir = backend_root / "tests"
    if not tests_dir.is_dir():
        return {"literal_user_ids": [], "pattern_hits_sample": [], "files_scanned": 0}

    files_scanned = 0
    for path in tests_dir.rglob("*.py"):
        files_scanned += 1
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in USER_ID_IN_TEST_RE.finditer(content):
            literal_ids.add(int(m.group(1)))
        if "@t.local" in content or "@test.local" in content:
            pattern_hits.append({"file": str(path.relative_to(backend_root))})
    return {
        "literal_user_ids": sorted(literal_ids),
        "literal_user_ids_count": len(literal_ids),
        "pattern_hits_sample": pattern_hits[:40],
        "pattern_hits_count": len(pattern_hits),
        "files_scanned": files_scanned,
    }


def _build_real_user_whitelist(
    all_users: list[dict[str, Any]], pattern_test_ids: set[int]
) -> list[dict[str, Any]]:
    """
    Cuentas humanas/administrativas reales conocidas.
    Evidencia: no coincide SQL_TEST_USER_WHERE, admin@local, roles reales.
    """
    whitelist: list[dict[str, Any]] = []
    for u in all_users:
        uid = u["id"]
        username = (u.get("username") or "").lower()
        email = (u.get("email") or "").lower()
        evidence: list[str] = []
        is_test_pattern = uid in pattern_test_ids

        if uid == 1:
            evidence.append("user_id_1_admin_fallback")
        if username == "admin" or email == "admin@local":
            evidence.append("admin_account_db")
        if not is_test_pattern:
            evidence.append("not_sql_test_user_pattern")
            if "@" in email and not email.endswith(("@t.local", "@test.local")):
                evidence.append("non_test_email_domain")
            if u.get("role") in ("admin", "usuario", "relevador") and not is_test_pattern:
                evidence.append(f"role_{u.get('role')}")

        if evidence and not is_test_pattern:
            whitelist.append(
                {
                    "id": uid,
                    "username": u.get("username"),
                    "email": u.get("email"),
                    "role": u.get("role"),
                    "is_active": bool(u.get("is_active")),
                    "created_at": str(u.get("created_at")),
                    "legitimacy_evidence": evidence,
                }
            )
    return whitelist


def _is_system_admin_preserve(user: dict[str, Any]) -> bool:
    uid = user["id"]
    username = (user.get("username") or "").lower()
    email = (user.get("email") or "").lower()
    return uid == 1 or username == "admin" or email == "admin@local"


def _test_provenance_for_user(
    user: dict[str, Any],
    pattern_test_ids: set[int],
    fixture_literal_ids: set[int],
) -> dict[str, Any]:
    uid = user["id"]
    pattern_evidence = uid in pattern_test_ids
    fixture_evidence = uid in fixture_literal_ids
    username = (user.get("username") or "").lower()
    email = (user.get("email") or "").lower()

    corroborating: list[str] = []
    if pattern_evidence:
        corroborating.append("sql_test_user_where_match")
    if fixture_evidence:
        corroborating.append("literal_id_in_test_file")
    if email.endswith(("@t.local", "@test.local")):
        corroborating.append("test_email_domain")
    if re.match(
        r"^(op_ruta3_|rlist_|edn_|op_ruta4_|op6f_|op6i_|op6j_|op7d_|op1b_|pr111_|pr11f_|"
        r"crudmapa_|stab7_|fix7_|fix10a_|qa_|hotfix_|reenc_|relhot_|outd_|rec_of_|rec_|"
        r"prod_|nr_|ind_|cnt_|ed4b_|rein_b_|reenc_of_|id10c_|st4_|hist_|cp_|cdoc_|u1_|"
        r"create_|act_|ina_|est_op_|inactive_)",
        username,
    ):
        corroborating.append("username_test_prefix")

    confirmed = pattern_evidence and len(corroborating) >= 1
    return {
        "user_id": uid,
        "pattern_evidence": pattern_evidence,
        "corroborating_evidence": corroborating,
        "confirmed_test": confirmed,
        "note": (
            "CONFIRMADO_TEST requiere SQL_TEST_USER_WHERE + corroboración; "
            "patrones solos sin SQL match no bastan"
        ),
    }


def _classify_all_users(
    all_users: list[dict[str, Any]],
    ref_map: dict[int, dict[str, Any]],
    whitelist_ids: set[int],
    provenance_by_id: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    by_class: dict[str, list[dict[str, Any]]] = {b: [] for b in CLASSIFICATION_BUCKETS}
    per_user: dict[int, dict[str, Any]] = {}

    for u in all_users:
        uid = u["id"]
        refs = ref_map.get(uid, {"ref_count_total": 0, "refs_by_table": {}, "refs_detail": []})
        fk_free = refs["ref_count_total"] == 0
        prov = provenance_by_id[uid]
        confirmed_test = prov["confirmed_test"]

        if _is_system_admin_preserve(u):
            cls = "SYSTEM_OR_ADMIN_PRESERVE"
            reason = "user_id_1_or_admin_account"
        elif uid in whitelist_ids:
            cls = "REAL_PROTECTED_USER"
            reason = "real_user_whitelist"
        elif confirmed_test and fk_free:
            cls = "CONFIRMADO_TEST_FK_FREE"
            reason = "confirmed_test_zero_fk"
        elif confirmed_test and not fk_free:
            cls = "CONFIRMADO_TEST_BLOCKED"
            reason = "confirmed_test_has_fk"
        elif not confirmed_test and fk_free:
            cls = "INDETERMINATE_FK_FREE"
            reason = "insufficient_test_evidence_zero_fk"
        else:
            cls = "INDETERMINATE_BLOCKED"
            reason = "insufficient_test_evidence_has_fk"

        entry = {
            "id": uid,
            "username": u.get("username"),
            "email": u.get("email"),
            "role": u.get("role"),
            "is_active": bool(u.get("is_active")),
            "classification": cls,
            "classification_reason": reason,
            "ref_count_total": refs["ref_count_total"],
            "refs_by_table": refs["refs_by_table"],
            "test_provenance": prov,
        }
        by_class[cls].append(entry)
        per_user[uid] = entry

    summary = {b: len(by_class[b]) for b in CLASSIFICATION_BUCKETS}
    return {
        "summary": summary,
        "total_classified": sum(summary.values()),
        "by_class": {b: [x["id"] for x in by_class[b]] for b in CLASSIFICATION_BUCKETS},
        "per_user_sample": {
            str(uid): per_user[uid]
            for uid in sorted(per_user.keys())[:20]
        },
        "entries_by_class": by_class,
    }


def _admin_fallback_analysis(conn: Connection, fk_edges: list[dict[str, Any]]) -> dict[str, Any]:
    """Cuantifica registros con created_by_user_id=1 y otras columnas user_id=1."""
    by_table: list[dict[str, Any]] = []
    total_refs_user_1 = 0
    for edge in fk_edges:
        tbl = edge["child_table"]
        col = edge["child_column"]
        cnt = int(_scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` = 1") or 0)
        if cnt:
            by_table.append(
                {
                    "table": tbl,
                    "column": col,
                    "refs_user_1": cnt,
                    "delete_rule": edge["delete_rule"],
                }
            )
            total_refs_user_1 += cnt
    return {
        "user_id": 1,
        "total_physical_refs": total_refs_user_1,
        "by_table": sorted(by_table, key=lambda x: -x["refs_user_1"]),
        "note": (
            "created_by_user_id=1 puede ser fallback histórico sin JWT; "
            "no implica que user 1 sea test ni que el registro hijo sea real"
        ),
    }


def _blocker_distribution(
    conn: Connection, blocked_user_ids: set[int], fk_edges: list[dict[str, Any]]
) -> dict[str, Any]:
    """Distribución de blockers para usuarios con FK sobrevivientes."""
    table_agg: dict[str, dict[str, Any]] = {}
    for edge in fk_edges:
        tbl = edge["child_table"]
        col = edge["child_column"]
        for chunk in _chunk_ids(blocked_user_ids, 400):
            ph = ",".join(str(u) for u in chunk)
            rows = conn.execute(
                text(
                    f"""
                    SELECT `{col}` AS uid, COUNT(*) AS cnt
                    FROM `{tbl}`
                    WHERE `{col}` IN ({ph})
                    GROUP BY `{col}`
                    """
                )
            ).fetchall()
            agg = table_agg.setdefault(
                tbl,
                {"blocker_table": tbl, "column": col, "distinct_users": set(), "physical_refs": 0},
            )
            for uid, cnt in rows:
                agg["distinct_users"].add(int(uid))
                agg["physical_refs"] += int(cnt)

    distribution = [
        {
            "blocker_table": tbl,
            "column": agg["column"],
            "distinct_users": len(agg["distinct_users"]),
            "physical_refs": agg["physical_refs"],
        }
        for tbl, agg in sorted(table_agg.items(), key=lambda x: -x[1]["physical_refs"])
    ]
    return {
        "blocked_users_total": len(blocked_user_ids),
        "blocker_distribution": distribution,
    }


def _auth_child_effects(conn: Connection, safe_user_ids: set[int]) -> dict[str, Any]:
    effects: dict[str, Any] = {}
    for table, col, rule in AUTH_CHILD_TABLES:
        total = _count(conn, table)
        cascade = 0
        if safe_user_ids:
            for chunk in _chunk_ids(safe_user_ids, 400):
                ph = ",".join(str(u) for u in chunk)
                cascade += int(
                    _scalar(conn, f"SELECT COUNT(*) FROM `{table}` WHERE `{col}` IN ({ph})") or 0
                )
        effects[table] = {
            "fk_column": col,
            "delete_rule": rule,
            "physical_rows_before": total,
            "cascade_rows_for_safe_users": cascade,
            "physical_rows_after_simulated": total - cascade,
        }
    return effects


def _delete_fk_graph_simulation(
    conn: Connection, safe_user_ids: set[int], fk_edges: list[dict[str, Any]]
) -> dict[str, Any]:
    """Simula CASCADE/SET NULL/RESTRICT al borrar SAFE users."""
    cascade_total = 0
    set_null_total = 0
    restrict_total = 0
    by_table: list[dict[str, Any]] = []

    for edge in fk_edges:
        tbl = edge["child_table"]
        col = edge["child_column"]
        rule = edge["delete_rule"]
        cnt = 0
        if safe_user_ids:
            for chunk in _chunk_ids(safe_user_ids, 400):
                ph = ",".join(str(u) for u in chunk)
                cnt += int(
                    _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` IN ({ph})") or 0
                )
        if cnt == 0:
            continue
        entry = {
            "child_table": tbl,
            "child_column": col,
            "delete_rule": rule,
            "rows_affected": cnt,
        }
        by_table.append(entry)
        if rule == "CASCADE":
            cascade_total += cnt
        elif rule == "SET NULL":
            set_null_total += cnt
        elif rule in ("RESTRICT", "NO ACTION"):
            restrict_total += cnt

    return {
        "safe_users_count": len(safe_user_ids),
        "cascade_rows": cascade_total,
        "set_null_rows": set_null_total,
        "restrict_rows": restrict_total,
        "restrict_expected_zero": restrict_total == 0,
        "by_child_table": sorted(by_table, key=lambda x: -x["rows_affected"]),
    }


def _users_uniqueness_audit(conn: Connection) -> dict[str, Any]:
    return {
        "username_unique_violations": _scalar(
            conn,
            "SELECT COUNT(*) - COUNT(DISTINCT username) FROM users",
        ),
        "email_unique_violations": _scalar(
            conn,
            "SELECT COUNT(*) - COUNT(DISTINCT email) FROM users",
        ),
        "note": "unicidad solo metadata; no motivo para borrar",
    }


def _juzgado_922_guard(conn: Connection) -> dict[str, Any]:
    exists = bool(_scalar(conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE id = :jz", {"jz": JUZGADO_922}))
    refs = int(_scalar(conn, "SELECT COUNT(*) FROM oficio WHERE juzgado_id = :jz", {"jz": JUZGADO_922}) or 0)
    return {
        "juzgado_id": JUZGADO_922,
        "exists": exists,
        "fk_refs_current": refs,
        "status": "READY_FOR_PHASE2E" if exists and refs == 0 else "NOT_READY",
        "no_delete_in_2d": True,
    }


def _protected_closure_for_safe_users(
    conn: Connection,
    safe_user_ids: set[int],
    protected_path: Path,
    fk_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    """Virtual delete users + verificar que no toca protected operational graph."""
    prot = expand_protected_indirect(conn, load_protected_sets(load_manifest(protected_path)))
    virtual = VirtualDeleteState()
    virtual.add_explicit("users", safe_user_ids)
    closure = protection_closure_check(virtual, prot)

    # SAFE users deben ser FK-free; cualquier hit aquí invalidaría el set.
    fk_hits: list[dict[str, Any]] = []
    if safe_user_ids:
        for edge in fk_edges:
            tbl = edge["child_table"]
            col = edge["child_column"]
            for chunk in _chunk_ids(safe_user_ids, 200):
                ph = ",".join(str(u) for u in chunk)
                cnt = int(
                    _scalar(conn, f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` IN ({ph})") or 0
                )
                if cnt:
                    fk_hits.append(
                        {"table": tbl, "column": col, "refs": cnt, "delete_rule": edge["delete_rule"]}
                    )

    return {
        "safe_users_count": len(safe_user_ids),
        "protection_closure": closure,
        "safe_user_fk_hits": fk_hits,
        "intersection_operational_protected": len(fk_hits),
        "valid": closure.get("valid", False) and len(fk_hits) == 0,
    }


def _recommendation(
    classification: dict[str, Any],
    safe_ids: list[int],
    protected_closure: dict[str, Any],
    delete_sim: dict[str, Any],
) -> dict[str, Any]:
    safe_count = len(safe_ids)
    indet = (
        classification["summary"]["INDETERMINATE_FK_FREE"]
        + classification["summary"]["INDETERMINATE_BLOCKED"]
    )
    blocked_test = classification["summary"]["CONFIRMADO_TEST_BLOCKED"]

    if safe_count == 0:
        choice = "C"
        label = "STOP"
        reason = "Sin candidatos SAFE_USERS_2D con evidencia concluyente y FK-free"
    elif not protected_closure.get("valid") or not delete_sim.get("restrict_expected_zero"):
        choice = "C"
        label = "STOP"
        reason = "Protected closure inválida o RESTRICT rows > 0 en simulación"
    elif indet > 0:
        choice = "B"
        label = "PARTIAL"
        reason = (
            f"SAFE={safe_count} demostrados; {indet} INDETERMINATE y "
            f"{blocked_test} CONFIRMADO_TEST_BLOCKED requieren KEEP"
        )
    else:
        choice = "A"
        label = "FREEZE_2D"
        reason = f"SAFE_USERS_2D={safe_count} suficientemente demostrados para manifest freeze"

    return {
        "choice": choice,
        "label": label,
        "reason": reason,
        "safe_users_count": safe_count,
        "blocked_test_users_count": blocked_test,
        "indeterminate_count": indet,
    }


def run_users_phase2d_diag(
    conn: Connection,
    *,
    protected_path: Path,
    manifest_paths: list[Path],
    backend_root: Path,
) -> dict[str, Any]:
    """Orquestador diagnóstico FASE 2D USERS."""
    baseline = _baseline_check(conn)
    all_users = _load_all_users(conn)
    users_total = len(all_users)

    fk_edges = load_all_user_foreign_keys(conn)
    ref_map = _compute_user_ref_map(conn, fk_edges)

    fk_free_ids = sorted(
        u["id"] for u in all_users if ref_map.get(u["id"], {}).get("ref_count_total", 0) == 0
    )
    fk_blocked_ids = sorted(set(u["id"] for u in all_users) - set(fk_free_ids))

    pattern_test_ids = _pattern_test_user_ids(conn)
    fixture_scan = _scan_test_fixture_user_ids(backend_root)
    fixture_literal_ids = set(fixture_scan.get("literal_user_ids", []))

    whitelist = _build_real_user_whitelist(all_users, pattern_test_ids)
    whitelist_ids = {w["id"] for w in whitelist}

    provenance_by_id: dict[int, dict[str, Any]] = {}
    for u in all_users:
        provenance_by_id[u["id"]] = _test_provenance_for_user(
            u, pattern_test_ids, fixture_literal_ids
        )

    classification = _classify_all_users(all_users, ref_map, whitelist_ids, provenance_by_id)

    safe_entries = classification["entries_by_class"]["CONFIRMADO_TEST_FK_FREE"]
    safe_ids = sorted(e["id"] for e in safe_entries)
    safe_set = set(safe_ids)

    blocked_test_entries = classification["entries_by_class"]["CONFIRMADO_TEST_BLOCKED"]
    blocked_test_users = [
        {
            "user_id": e["id"],
            "username": e.get("username"),
            "ref_count_total": e["ref_count_total"],
            "tables": e["refs_by_table"],
            "test_provenance": e["test_provenance"],
        }
        for e in sorted(blocked_test_entries, key=lambda x: -x["ref_count_total"])[:200]
    ]

    all_blocked_ids = set(fk_blocked_ids)
    blocker_dist = _blocker_distribution(conn, all_blocked_ids, fk_edges)
    test_blocker_audit = audit_user_blockers(conn, pattern_test_ids)

    admin_fallback = _admin_fallback_analysis(conn, fk_edges)
    auth_effects = _auth_child_effects(conn, safe_set)
    delete_fk_sim = _delete_fk_graph_simulation(conn, safe_set, fk_edges)
    protected_closure = _protected_closure_for_safe_users(conn, safe_set, protected_path, fk_edges)

    known = _load_known_test_ids_from_manifests(manifest_paths)
    known_test_guards = _known_test_guard(conn, known)
    juzgado_guard = _juzgado_922_guard(conn)

    safe_active = sum(1 for e in safe_entries if e.get("is_active"))
    safe_inactive = len(safe_entries) - safe_active

    post_users = users_total - len(safe_ids)

    fk_free_drift = len(fk_free_ids) - USERS_FK_FREE_ORIENTATIVE

    return {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-CLEANUP.3L-DIAG",
        "phase": "FASE_2D_USERS",
        "mode": "READ_ONLY_DIAG",
        "writes_executed": False,
        "baseline": baseline,
        "users_total": users_total,
        "fk_schema": {
            "ALL_USER_FOREIGN_KEYS": fk_edges,
            "edge_count": len(fk_edges),
        },
        "fk_free_users": {
            "count": len(fk_free_ids),
            "ids": fk_free_ids,
            "orientative_expected": USERS_FK_FREE_ORIENTATIVE,
            "drift_vs_orientative": fk_free_drift,
            "drift_explanation": (
                f"Recalculado desde INFORMATION_SCHEMA: {len(fk_free_ids)} vs "
                f"orientativo {USERS_FK_FREE_ORIENTATIVE} (delta {fk_free_drift:+d})"
            ),
        },
        "fk_blocked_users": {
            "count": len(fk_blocked_ids),
            "ids_sample": fk_blocked_ids[:50],
        },
        "classification_summary": classification["summary"],
        "classification_reconciliation": {
            "sum_buckets": sum(classification["summary"].values()),
            "equals_users_total": sum(classification["summary"].values()) == users_total,
            "breakdown": classification["summary"],
            "explanation": (
                f"{classification['summary']['CONFIRMADO_TEST_FK_FREE']} CONFIRMADO_TEST_FK_FREE + "
                f"{classification['summary']['CONFIRMADO_TEST_BLOCKED']} CONFIRMADO_TEST_BLOCKED + "
                f"{classification['summary']['REAL_PROTECTED_USER']} REAL_PROTECTED + "
                f"{classification['summary']['SYSTEM_OR_ADMIN_PRESERVE']} SYSTEM_ADMIN + "
                f"{classification['summary']['INDETERMINATE_FK_FREE']} INDET_FK_FREE + "
                f"{classification['summary']['INDETERMINATE_BLOCKED']} INDET_BLOCKED = {users_total}"
            ),
        },
        "real_user_whitelist": whitelist,
        "system_admin_preserve": [
            e for e in classification["entries_by_class"]["SYSTEM_OR_ADMIN_PRESERVE"]
        ],
        "test_provenance": {
            "sql_test_user_where_count": len(pattern_test_ids),
            "fixture_scan": fixture_scan,
            "confirmed_test_total": sum(
                1 for p in provenance_by_id.values() if p["confirmed_test"]
            ),
        },
        "safe_users": {
            "SAFE_USERS_2D": safe_ids,
            "count": len(safe_ids),
            "active_true": safe_active,
            "active_false": safe_inactive,
            "entries_sample": safe_entries[:30],
        },
        "blocked_test_users": {
            "count": len(blocked_test_entries),
            "entries": blocked_test_users,
            "audit": test_blocker_audit,
        },
        "indeterminate_users": {
            "INDETERMINATE_FK_FREE": classification["by_class"]["INDETERMINATE_FK_FREE"],
            "INDETERMINATE_BLOCKED": classification["by_class"]["INDETERMINATE_BLOCKED"],
            "count_fk_free": classification["summary"]["INDETERMINATE_FK_FREE"],
            "count_blocked": classification["summary"]["INDETERMINATE_BLOCKED"],
        },
        "keep_sets": {
            "KEEP_REAL_USERS": classification["by_class"]["REAL_PROTECTED_USER"],
            "KEEP_SYSTEM_USERS": classification["by_class"]["SYSTEM_OR_ADMIN_PRESERVE"],
            "KEEP_INDETERMINATE_USERS": (
                classification["by_class"]["INDETERMINATE_FK_FREE"]
                + classification["by_class"]["INDETERMINATE_BLOCKED"]
            ),
        },
        "blocker_distribution": blocker_dist,
        "auth_child_effects": auth_effects,
        "cascade_simulation": {
            "auth_and_profile": auth_effects,
            "delete_fk_graph": delete_fk_sim,
        },
        "set_null_simulation": {
            "set_null_rows": delete_fk_sim["set_null_rows"],
            "by_child_table": [
                x for x in delete_fk_sim["by_child_table"] if x["delete_rule"] == "SET NULL"
            ],
        },
        "admin_fallback_analysis": admin_fallback,
        "protected_closure": protected_closure,
        "post_count_simulation": {
            "users_before": users_total,
            "safe_delete_count": len(safe_ids),
            "users_after": post_users,
            "profiles_before": auth_effects["profiles"]["physical_rows_before"],
            "profiles_cascade": auth_effects["profiles"]["cascade_rows_for_safe_users"],
            "profiles_after": auth_effects["profiles"]["physical_rows_after_simulated"],
            "password_reset_before": auth_effects["password_reset_codes"]["physical_rows_before"],
            "password_reset_cascade": auth_effects["password_reset_codes"]["cascade_rows_for_safe_users"],
        },
        "users_uniqueness": _users_uniqueness_audit(conn),
        "juzgado_922_guard": juzgado_guard,
        "known_test_guards": known_test_guards,
        "catalog_metadata_preserve": {
            "relevador_qa_id_2": "Otro Relevador QA — NO DELETE",
            "juzgado_922": JUZGADO_922,
            "calles_test": 6,
            "rubros_qa_pendientes": True,
            "no_catalog_delete_in_2d": True,
        },
        "recommendation": _recommendation(
            classification, safe_ids, protected_closure, delete_fk_sim
        ),
        "source_protected_manifest": str(protected_path.resolve()),
    }


def write_diag_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
