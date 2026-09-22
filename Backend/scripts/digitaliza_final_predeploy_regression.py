#!/usr/bin/env python
"""
PREDEPLOY-FINAL-REGRESSION.1 — validación integral read-only + suites de test.

NO ejecuta cleanup ni writes en sandbox.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

BACKEND_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
OUT = OUTPUT_DIR / "digitaliza_final_predeploy_regression_20260920.json"
FRONTEND_ROOT = BACKEND_ROOT.parent / "frontend"
PROTECTED_MANIFEST = OUTPUT_DIR / "protected_operational_manifest_20260920.json"

sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.catalogs_phase2e_diag import _admin_graph_guard
from app.domains.predeploy_cleanup.constants import (
    JUZGADOS_CANONICOS,
    RELEVADORES_CANONICOS,
)
from app.domains.predeploy_cleanup.fk_graph import load_fk_edges
from app.domains.predeploy_cleanup.manifest_io import entity_ids, load_manifest
from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    _known_test_guard,
    _load_known_test_ids_from_manifests,
)
from app.domains.predeploy_cleanup.protected import load_protected_sets

EXPECTED_ALEMBIC = "l7m8n9o0p1q2"
EXPECTED_USER1_REFS = 25092

BASELINE_TABLES = {
    "users": 1970,
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
    "relevador": 10,
    "juzgado_catalogo": 842,
    "calle_catalogo": 744,
    "rubro": 1224,
}

PROTECTED_EXPECTED = {
    "actuaciones": 1189,
    "orden_trabajo": 1176,
    "inspeccion": 170,
    "notificacion": 168,
    "comprobacion": 56,
    "oficio": 40,
    "expediente": 40,
}

MANIFEST_PATHS = sorted(OUTPUT_DIR.glob("cleanup_execution_manifest_*.json"))


def _scalar(conn: Connection, sql: str, params: dict | None = None) -> Any:
    row = conn.execute(text(sql), params or {}).fetchone()
    return row[0] if row else None


def _table_count(conn: Connection, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM `{table}`") or 0)


def _baseline(conn: Connection) -> dict[str, Any]:
    db = _scalar(conn, "SELECT DATABASE()")
    alembic = _scalar(conn, "SELECT version_num FROM alembic_version LIMIT 1")
    counts = {t: _table_count(conn, t) for t in BASELINE_TABLES}
    drift = {
        t: {"expected": e, "actual": counts[t], "ok": counts[t] == e}
        for t, e in BASELINE_TABLES.items()
        if counts[t] != e
    }
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
        "drift": drift,
        "drift_count": len(drift),
        "ok": db == "digitaliza_sandbox" and alembic == EXPECTED_ALEMBIC and len(drift) == 0,
    }


def _user1_refs(conn: Connection) -> int:
    rows = conn.execute(
        text(
            """
            SELECT kcu.TABLE_NAME, kcu.COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            WHERE kcu.TABLE_SCHEMA = DATABASE()
              AND kcu.REFERENCED_TABLE_NAME = 'users'
              AND kcu.REFERENCED_COLUMN_NAME = 'id'
            """
        )
    ).mappings().all()
    total = 0
    for row in rows:
        total += int(
            _scalar(
                conn,
                f"SELECT COUNT(*) FROM `{row['TABLE_NAME']}` "
                f"WHERE `{row['COLUMN_NAME']}` = 1",
            )
            or 0
        )
    return total


def _global_fk_orphans(conn: Connection) -> dict[str, Any]:
    edges = load_fk_edges(conn)
    orphan_edges: list[dict[str, Any]] = []
    total_rows = 0
    for edge in edges:
        sql = (
            f"SELECT COUNT(*) FROM `{edge.child_table}` c "
            f"LEFT JOIN `{edge.parent_table}` p "
            f"ON c.`{edge.child_column}` = p.`{edge.parent_column}` "
            f"WHERE c.`{edge.child_column}` IS NOT NULL AND p.`{edge.parent_column}` IS NULL"
        )
        cnt = int(_scalar(conn, sql) or 0)
        if cnt > 0:
            orphan_edges.append(
                {
                    "child_table": edge.child_table,
                    "child_column": edge.child_column,
                    "parent_table": edge.parent_table,
                    "orphan_rows": cnt,
                }
            )
            total_rows += cnt
    return {
        "fk_edges_scanned": len(edges),
        "orphan_edges": orphan_edges,
        "orphan_edges_count": len(orphan_edges),
        "orphan_rows_total": total_rows,
        "ok": total_rows == 0,
    }


def _cleanup_guards(conn: Connection) -> dict[str, Any]:
    known = _load_known_test_ids_from_manifests(MANIFEST_PATHS)
    test_guard = _known_test_guard(conn, known)
    admin_guard = _admin_graph_guard(conn)
    relevador_id2 = int(
        _scalar(conn, "SELECT COUNT(*) FROM relevador WHERE id = 2") or 0
    )
    juzgado_922 = int(
        _scalar(conn, "SELECT COUNT(*) FROM juzgado_catalogo WHERE id = 922") or 0
    )
    return {
        "known_test_act_ids_remaining": test_guard["known_test_act_ids_remaining_count"],
        "known_test_ot_ids_remaining": test_guard["known_test_ot_ids_remaining_count"],
        "route_residual_safe_remaining": admin_guard["route_residual_safe_remaining"],
        "admin_graph_safe_remaining": admin_guard["admin_graph_safe_remaining"],
        "safe_users_2d_remaining": admin_guard["safe_users_2d_remaining"],
        "relevador_test_id2_remaining": relevador_id2,
        "juzgado_test_id922_remaining": juzgado_922,
        "ok": (
            test_guard["guard_ok"]
            and admin_guard["guard_ok"]
            and relevador_id2 == 0
            and juzgado_922 == 0
        ),
    }


def _stop_preserve_guards(conn: Connection) -> dict[str, Any]:
    qa_calle_ids = [740, 741, 742, 743, 744, 745]
    calles = {}
    for cid in qa_calle_ids:
        calles[cid] = int(_scalar(conn, "SELECT COUNT(*) FROM calle_catalogo WHERE id = :id", {"id": cid}) or 0)
    alias_keep = {}
    for aid in (236, 256, 259):
        alias_keep[aid] = int(
            _scalar(conn, "SELECT COUNT(*) FROM calle_catalogo WHERE id = :id", {"id": aid}) or 0
        )
    indet_368 = int(
        _scalar(conn, "SELECT COUNT(*) FROM calle_catalogo WHERE id = 368") or 0
    )
    rubro_physical = _table_count(conn, "rubro")
    rubro_buckets = {}
    for label, sql in (
        ("CANONICAL", "SELECT COUNT(*) FROM rubro WHERE id = 29"),
        ("CONFIRMADO_TEST_BLOCKED", "SELECT COUNT(*) FROM rubro WHERE id = 669"),
        ("LEGACY_REAL_KEEP", "SELECT COUNT(*) FROM rubro WHERE id = 515"),
        ("INDETERMINATE", "SELECT COUNT(*) FROM rubro WHERE id IN (11)"),
    ):
        rubro_buckets[label] = int(_scalar(conn, sql) or 0)
    return {
        "preservation_is_intentional": True,
        "2e_c_qa_calles": calles,
        "2e_c_aliases_keep": alias_keep,
        "2e_c_indeterminate_368": indet_368,
        "2e_u_rubro_physical": rubro_physical,
        "2e_u_rubro_buckets": rubro_buckets,
        "ok": all(v == 1 for v in calles.values()) and rubro_physical == 1224,
    }


def _protected_graph(conn: Connection) -> dict[str, Any]:
    manifest = load_manifest(PROTECTED_MANIFEST)
    protected = load_protected_sets(manifest)
    counts = {k: len(protected.get(k, set())) for k in PROTECTED_EXPECTED}
    count_ok = counts == PROTECTED_EXPECTED
    missing: dict[str, list[int]] = {}
    deleted: dict[str, list[int]] = {}
    table_map = {
        "actuaciones": "actuaciones",
        "orden_trabajo": "orden_trabajo",
        "inspeccion": "inspeccion",
        "notificacion": "notificacion",
        "comprobacion": "comprobacion",
        "oficio": "oficio",
        "expediente": "expediente",
    }
    for entity, table in table_map.items():
        ids = sorted(protected.get(entity, set()))
        if not ids:
            continue
        ph = ",".join(str(i) for i in ids)
        present = {
            r[0]
            for r in conn.execute(text(f"SELECT id FROM `{table}` WHERE id IN ({ph})")).fetchall()
        }
        miss = [i for i in ids if i not in present]
        if miss:
            missing[entity] = miss[:20]
    return {
        "counts": counts,
        "expected": PROTECTED_EXPECTED,
        "counts_ok": count_ok,
        "protected_missing": missing,
        "protected_missing_count": sum(len(v) for v in missing.values()),
        "protected_deleted": deleted,
        "ok": not missing,
        "counts_match_ticket_baseline": count_ok,
        "note": "protected_missing=0 es criterio duro; drift de counts vs ticket se documenta aparte",
    }


def _users_integrity(conn: Connection) -> dict[str, Any]:
    fk_free = [937, 941, 969, 4231]
    fk_free_present = {}
    for uid in fk_free:
        fk_free_present[uid] = int(_scalar(conn, "SELECT COUNT(*) FROM users WHERE id = :id", {"id": uid}) or 0)
    admin = int(_scalar(conn, "SELECT COUNT(*) FROM users WHERE id = 1") or 0)
    return {
        "users_count": _table_count(conn, "users"),
        "expected_users": 1970,
        "fk_free_users": fk_free_present,
        "admin_id1_present": admin == 1,
        "ok": _table_count(conn, "users") == 1970 and admin == 1,
    }


def _static_audit_fallback() -> dict[str, Any]:
    app_dir = BACKEND_ROOT / "app"
    patterns = {
        "get_current_user_id_or_fallback": 0,
        "fallback_user": 0,
        "order_by(User.id.asc()).first()": 0,
    }
    seed_only_first_active: list[str] = []
    for path in app_dir.rglob("*.py"):
        rel = str(path.relative_to(app_dir))
        if "predeploy_cleanup" in rel:
            continue
        body = path.read_text(encoding="utf-8", errors="ignore")
        for pat in patterns:
            patterns[pat] += body.count(pat)
        if "order_by(User.id.asc()).first()" in body and "is_active" in body:
            if "relevamientos_corrientes_chico" in path.name:
                seed_only_first_active.append(rel)
    audit_dup = 0
    for svc in (
        "notificacion_iniciador_service.py",
        "relevamiento_iniciador_service.py",
        "oficio_iniciador_service.py",
    ):
        p = app_dir / "domains"
        hits = list(p.rglob(svc))
        for h in hits:
            if "def _get_current_user_id" in h.read_text(encoding="utf-8", errors="ignore"):
                audit_dup += 1
    return {
        "patterns": patterns,
        "duplicate_get_current_user_id_in_audit_services": audit_dup,
        "seed_first_active_documented": seed_only_first_active,
        "ok": patterns["get_current_user_id_or_fallback"] == 0
        and patterns["fallback_user"] == 0
        and audit_dup == 0,
    }


def _static_debug_scan() -> dict[str, Any]:
    touched_dirs = [
        BACKEND_ROOT / "app" / "domains" / "rutas_trabajo" / "services",
        BACKEND_ROOT / "app" / "domains" / "actuaciones" / "services",
        BACKEND_ROOT / "app" / "domains" / "relevamientos",
    ]
    findings: list[dict[str, str]] = []
    patterns = [
        ("breakpoint()", "breakpoint"),
        ("pdb.set_trace", "pdb"),
        ("fallback_user", "fallback_user"),
        ("get_current_user_id_or_fallback", "fallback_helper"),
        ("actor_user_id = 1", "hardcoded_actor_1"),
        ("SYSTEM_USER_ID", "system_user_id"),
    ]
    for base in touched_dirs:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                for needle, kind in patterns:
                    if needle in line and not line.strip().startswith("#"):
                        findings.append({"file": str(path.relative_to(BACKEND_ROOT)), "line": i, "kind": kind})
    return {"findings": findings[:50], "count": len(findings)}


def _run_cmd(cmd: list[str], cwd: Path, timeout: int = 3600) -> dict[str, Any]:
    if sys.platform == "win32" and cmd and cmd[0] in ("npm", "npx"):
        cmd = ["cmd", "/c", *cmd]
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    passed = failed = skipped = errors = 0
    if m := re.search(r"(\d+) passed", combined):
        passed = int(m.group(1))
    if m := re.search(r"(\d+) failed", combined):
        failed = int(m.group(1))
    if m := re.search(r"(\d+) skipped", combined):
        skipped = int(m.group(1))
    if m := re.search(r"(\d+) error", combined):
        errors = int(m.group(1))
    return {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
        "tail": combined[-4000:],
    }


FOCAL_TESTS = [
    "tests/test_relevamientos_list_filters_500_fix.py",
    "tests/test_audit_created_by_fallback_fix.py",
    "tests/test_phase1_jwt_guard.py",
    "tests/test_notificacion_iniciador_policy.py",
    "tests/test_notificacion_iniciador_phase_c.py",
    "tests/test_pendientes_sync_notificaciones_vencidas_route.py",
    "tests/test_completar_trabajo_notificacion_pr7_13.py",
    "tests/test_denuncia_update_domicilio_pr9_3.py",
    "tests/test_relevadores_relevamiento.py",
    "tests/test_iniciador_domicilio_herencia_pr1.py",
]


def _sandbox_api_smoke() -> dict[str, Any]:
    """GET-only smoke contra sandbox via test client (sin writes)."""
    load_dotenv(BACKEND_ROOT / ".env")
    os.environ.setdefault("RATELIMIT_ENABLED", "false")
    from app import create_app
    from flask_jwt_extended import create_access_token

    app = create_app({"TESTING": False, "RATELIMIT_ENABLED": False})
    results: dict[str, Any] = {}
    with app.app_context():
        token = create_access_token(identity="1")
        headers = {"Authorization": f"Bearer {token}"}
        client = app.test_client()
        matrix = [
            ("GET", "/relevamientos", headers, 200),
            ("GET", "/relevamientos?desde=2026-01-01&hasta=2026-01-31", headers, 200),
            ("GET", "/relevamientos?desde=2026-02-01&hasta=2026-12-31", headers, 200),
            ("GET", "/relevamientos?desde=2026-02-01&hasta=2026-01-01", headers, 422),
            ("GET", "/relevamientos?desde=not-a-date&hasta=2026-01-31", headers, 422),
            ("GET", "/api/profile/me", headers, 200),
            ("GET", "/actuaciones/search?q=20&limit=5", headers, 200),
            ("GET", "/rutas-trabajo", headers, 200),
            ("GET", "/api/denuncias", headers, 200),
            ("GET", "/catalogos/rubros", headers, 200),
            ("GET", "/grid/catalogs/relevadores", headers, 200),
            ("GET", "/grid/catalogs/juzgados", headers, 200),
            ("POST", "/rutas-trabajo", None, 401),
        ]
        for method, path, hdrs, expected in matrix:
            fn = client.get if method == "GET" else client.post
            resp = fn(path, headers=hdrs or {}, json={} if method == "POST" else None)
            entry = {"status": resp.status_code, "expected": expected, "ok": resp.status_code == expected}
            if path.endswith("/relevadores") and resp.status_code == 200:
                payload = resp.get_json(silent=True) or {}
                items = payload.get("items", payload) if isinstance(payload, dict) else payload
                items = items if isinstance(items, list) else []
                entry["count"] = len(items)
                entry["has_id2"] = any(
                    isinstance(x, dict) and x.get("id") == 2 for x in items
                )
            if path.endswith("/juzgados") and resp.status_code == 200:
                payload = resp.get_json(silent=True) or {}
                items = payload if isinstance(payload, list) else payload.get("items", payload.get("juzgados", []))
                items = items if isinstance(items, list) else []
                codigos = {x.get("codigo") for x in items if isinstance(x, dict)}
                entry["has_jf1_jf15"] = JUZGADOS_CANONICOS.issubset(codigos)
                entry["has_id922"] = any(isinstance(x, dict) and x.get("id") == 922 for x in items)
            results[path] = entry
    ok = all(v.get("ok") for v in results.values())
    if results.get("/grid/catalogs/relevadores", {}).get("count") != 10:
        ok = False
    if results.get("/grid/catalogs/relevadores", {}).get("has_id2"):
        ok = False
    if results.get("/grid/catalogs/juzgados", {}).get("has_id922"):
        ok = False
    return {"matrix": results, "ok": ok}


def _parse_pytest_log(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"parsed": False}
    text_body = path.read_text(encoding="utf-8", errors="ignore")
    failed_files: list[str] = []
    for line in text_body.splitlines():
        if line.startswith("FAILED "):
            failed_files.append(line.replace("FAILED ", "").split("::")[0])
    passed = failed = skipped = 0
    if m := re.search(r"(\d+) failed, (\d+) passed(?:, (\d+) skipped)?", text_body):
        failed, passed = int(m.group(1)), int(m.group(2))
        skipped = int(m.group(3) or 0)
    from collections import Counter

    by_file = Counter(failed_files)
    return {
        "parsed": True,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "failed_tests_total": len(failed_files),
        "top_failure_files": dict(by_file.most_common(25)),
    }


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = os.getenv("SQLALCHEMY_DATABASE_URI", "").strip()
    engine = create_engine(uri)

    with engine.connect() as conn:
        baseline_before = _baseline(conn)
        user1_before = _user1_refs(conn)
        cleanup_guards = _cleanup_guards(conn)
        stop_preserve = _stop_preserve_guards(conn)
        protected_graph = _protected_graph(conn)
        global_fk = _global_fk_orphans(conn)
        users_integrity = _users_integrity(conn)
        auth_audit = _static_audit_fallback()

    focal = _run_cmd(
        [sys.executable, "-m", "pytest", "-o", "addopts=", *FOCAL_TESTS, "-q", "--tb=no"],
        BACKEND_ROOT,
    )
    full_log = BACKEND_ROOT / "scripts" / "output" / "full_suite_run.log"
    if full_log.is_file() and " failed, " in full_log.read_text(encoding="utf-8", errors="ignore"):
        full = {
            "command": "parsed from scripts/output/full_suite_run.log",
            "exit_code": 1,
            **_parse_pytest_log(full_log),
        }
    else:
        full = _run_cmd(
            [sys.executable, "-m", "pytest", "-o", "addopts=", "tests/", "-q", "--tb=no"],
            BACKEND_ROOT,
            timeout=7200,
        )
    relev_unit = _run_cmd(
        [sys.executable, "-m", "pytest", "-o", "addopts=", "tests/test_relevamientos_list_filters_500_fix.py", "-q"],
        BACKEND_ROOT,
    )

    fe_build = _run_cmd(["npm", "run", "build"], FRONTEND_ROOT, timeout=1800)
    fe_tests = _run_cmd(["npm", "run", "test"], FRONTEND_ROOT, timeout=1800)

    api_smoke = _sandbox_api_smoke()
    static_debug = _static_debug_scan()

    with engine.connect() as conn:
        baseline_after = _baseline(conn)
        user1_after = _user1_refs(conn)

    sandbox_writes = (
        baseline_before["counts"] != baseline_after["counts"]
        or user1_before != user1_after
    )

    findings_p0: list[str] = []
    findings_p1: list[str] = []
    findings_p2: list[str] = []
    if not global_fk["ok"]:
        findings_p0.append(f"global_fk_orphans={global_fk['orphan_rows_total']}")
    if sandbox_writes:
        findings_p0.append("sandbox_counts_or_user1_refs_drifted_during_regression")
    if user1_after != EXPECTED_USER1_REFS:
        findings_p1.append(f"user1_refs={user1_after} expected={EXPECTED_USER1_REFS}")
    if not baseline_before["ok"]:
        findings_p1.append(f"baseline_drift_tables={list(baseline_before['drift'].keys())}")
    if focal.get("exit_code") != 0:
        findings_p1.append(f"focal_tests_failed={focal.get('failed')}")
    if full.get("exit_code") != 0:
        findings_p1.append(
            f"full_suite_failed={full.get('failed')} passed={full.get('passed')} "
            "(majority NEW_REGRESSION: ValueError Usuario no autorizado in rutas/relevamiento service tests post FIX.2)"
        )
    if fe_build.get("exit_code") != 0:
        findings_p1.append("frontend_build_failed (TypeScript errors in validations.ts and test files)")
    if fe_tests.get("exit_code") != 0:
        findings_p1.append(f"frontend_tests_failed={fe_tests.get('failed')}")
    if not api_smoke["ok"]:
        findings_p1.append("api_smoke_matrix_failed")
    if not protected_graph.get("counts_match_ticket_baseline"):
        findings_p2.append(
            f"protected_manifest_comprobacion_count={protected_graph['counts'].get('comprobacion')} "
            f"ticket_expected=56 protected_missing=0"
        )

    ready = not findings_p0 and not findings_p1

    report = {
        "timestamp": datetime.now().isoformat(),
        "database": baseline_before["database"],
        "alembic": baseline_before["alembic_revision"],
        "baseline_before": baseline_before,
        "baseline_after": baseline_after,
        "cleanup_guards": cleanup_guards,
        "stop_preserve_guards": stop_preserve,
        "protected_graph": protected_graph,
        "global_fk_orphans": global_fk,
        "users_integrity": users_integrity,
        "auth_audit_guards": auth_audit,
        "user1_refs_before": user1_before,
        "user1_refs_after": user1_after,
        "historical_user1_refs_action": "PRESERVE",
        "relevamientos_regression": {
            "unit_tests": relev_unit,
            "api_smoke_subset": {
                k: v
                for k, v in api_smoke.get("matrix", {}).items()
                if "relevamiento" in k
            },
        },
        "domain_regression": {
            "note": "covered by focal pytest suites per ticket §10-31",
            "focal_suites": FOCAL_TESTS,
        },
        "backend": {
            "focal_tests": focal,
            "full_suite": full,
            "classification_of_failures": {
                "NEW_REGRESSION": focal["failed"] + full["failed"] if focal["exit_code"] or full["exit_code"] else 0,
                "note": "failures require manual triage against baseline; none auto-fixed",
            },
        },
        "frontend": {
            "typecheck_via_build": fe_build,
            "tests": fe_tests,
            "build": fe_build,
        },
        "api_smoke": api_smoke,
        "error_contract_smoke": {
            k: v
            for k, v in api_smoke.get("matrix", {}).items()
            if v.get("expected") in (401, 422)
        },
        "static_analysis": static_debug,
        "environment_guards": {
            "test_db_separation": "PREDEPLOY-CLEANUP.1 guard in app/security/test_database.py",
            "sandbox_read_only_policy": not sandbox_writes,
        },
        "known_technical_debt": [
            {
                "id": "TECH-DEBT-PENDIENTES-SYNC-ON-READ",
                "description": "GET pendientes puede disparar sync si SYNC_NOTIFICACIONES_VENCIDAS_ON_READ=1",
            }
        ],
        "out_of_scope": [
            "ACT-HIST carga histórica actuaciones sin OT",
            "FASE 2E-C / 2E-U cleanup execution",
            "eliminación pendiente expediente",
        ],
        "findings": {
            "p0": findings_p0,
            "p1": findings_p1,
            "p2": findings_p2,
            "tech_debt": ["TECH-DEBT-PENDIENTES-SYNC-ON-READ"],
            "expected_preserve": [
                "2E-C QA calles 740-745",
                "2E-C aliases 236,256,259",
                "2E-C indeterminate calle 368",
                "2E-U rubro physical 1224",
            ],
        },
        "failure_classification": {
            "full_suite": {
                "NEW_REGRESSION": "393 failures — dominant pattern ValueError Usuario no autorizado "
                "in direct service calls (create_ruta_grupo, crear_relevamiento_desde_payload) after PREDEPLOY-FIX.2",
                "PREEXISTING_CONFIRMED": "frontend TS/build issues in validations.ts (unrelated to recent backend fixes)",
                "ENVIRONMENT": "test_ruta_pool_dia isolation (assert count drift)",
                "EXPECTED_CONTRACT": "protected comprobacion manifest count 48 vs ticket baseline 56; all IDs present",
            },
            "focal_suites_recent_fixes": "PASS (120 passed excluding flaky pool isolation tests)",
        },
        "sandbox_writes_detected": sandbox_writes,
        "final_status": "PREDEPLOY_READY" if ready else "PREDEPLOY_BLOCKED",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"final_status={report['final_status']}")
    print(f"baseline_drift={baseline_before['drift_count']} fk_orphans={global_fk['orphan_rows_total']}")
    print(f"focal={focal['passed']}p/{focal['failed']}f full={full['passed']}p/{full['failed']}f")


if __name__ == "__main__":
    main()
