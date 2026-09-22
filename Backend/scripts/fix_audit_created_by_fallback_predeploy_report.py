#!/usr/bin/env python
"""PREDEPLOY-FIX.2 — reporte post-fix audit fallback (read-only guards)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

OUT = BACKEND_ROOT / "scripts" / "output" / "audit_created_by_fallback_predeploy_fix_20260920.json"


def _baseline(conn) -> dict:
    counts = {}
    for table in ("users", "relevador", "juzgado_catalogo"):
        counts[table] = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
    alembic = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
    db = conn.execute(text("SELECT DATABASE()")).scalar()
    return {"database": db, "alembic_revision": alembic, "counts": counts}


def _user1_refs(conn) -> int:
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
            conn.execute(
                text(
                    f"SELECT COUNT(*) FROM `{row['TABLE_NAME']}` "
                    f"WHERE `{row['COLUMN_NAME']}` = 1"
                )
            ).scalar()
            or 0
        )
    return total


def _fallback_scan() -> dict:
    app_dir = BACKEND_ROOT / "app"
    patterns = {
        "get_current_user_id_or_fallback": 0,
        "fallback_user": 0,
        "order_by(User.id.asc()).first()": 0,
    }
    for path in app_dir.rglob("*.py"):
        if "predeploy_cleanup" in str(path):
            continue
        text_body = path.read_text(encoding="utf-8", errors="ignore")
        for pat in patterns:
            patterns[pat] += text_body.count(pat)
    return patterns


def _run_pytest() -> dict:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-o",
        "addopts=",
        "tests/test_audit_created_by_fallback_fix.py",
        "tests/test_notificacion_iniciador_policy.py",
        "tests/test_notificacion_iniciador_phase_c.py",
        "tests/test_pendientes_sync_notificaciones_vencidas_route.py",
        "tests/test_phase1_jwt_guard.py",
        "-q",
        "--tb=no",
    ]
    proc = subprocess.run(cmd, cwd=BACKEND_ROOT, capture_output=True, text=True)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    passed = failed = skipped = 0
    if m := re.search(r"(\d+) passed", combined):
        passed = int(m.group(1))
    if m := re.search(r"(\d+) failed", combined):
        failed = int(m.group(1))
    if m := re.search(r"(\d+) skipped", combined):
        skipped = int(m.group(1))
    return {
        "commands": [" ".join(cmd)],
        "exit_code": proc.returncode,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = os.getenv("SQLALCHEMY_DATABASE_URI", "").strip()
    engine = create_engine(uri)

    with engine.connect() as conn:
        pre = _baseline(conn)
        user1_pre = _user1_refs(conn)

    tests = _run_pytest()
    patterns_after = _fallback_scan()

    with engine.connect() as conn:
        post = _baseline(conn)
        user1_post = _user1_refs(conn)

    guards_ok = (
        pre == post
        and user1_pre == user1_post == 25092
        and pre["counts"]["users"] == 1970
    )

    report = {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-FIX.2",
        "files_changed": [
            "app/domains/rutas_trabajo/services/auth_service.py",
            "app/domains/actuaciones/services/notificacion_iniciador_service.py",
            "app/domains/relevamientos/services/relevamiento_iniciador_service.py",
            "app/domains/actuaciones/services/oficio_iniciador_service.py",
            "app/domains/actuaciones/services/cargar_actuacion_post_commit.py",
            "app/domains/actuaciones/pipelines/sync_notificaciones_vencidas.py",
            "app/domains/actuaciones/services/create_service.py",
            "app/domains/actuaciones/services/update_service.py",
            "app/domains/actuaciones/services/completar_trabajo_cierre_service.py",
            "app/domains/actuaciones/services/oficio_completion_service.py",
            "app/domains/relevamientos/services/create_service.py",
            "app/domains/denuncias/services/denuncias_service.py",
            "app/main.py",
            "tests/test_audit_created_by_fallback_fix.py",
            "tests/conftest.py",
        ],
        "helpers_removed": [
            "get_current_user_id_or_fallback",
            "_get_current_user_id (notificacion_iniciador_service)",
            "_get_current_user_id (relevamiento_iniciador_service)",
            "_get_current_user_id (oficio_iniciador_service)",
            "_get_current_user_id (denuncias_service)",
        ],
        "helpers_added_or_changed": [
            "get_current_user_id (strict JWT)",
            "validate_actor_user_id (explicit actor)",
            "resolve_actor_user_id (explicit or strict JWT)",
        ],
        "fallback_patterns_before": {
            "get_current_user_id_or_fallback": 1,
            "duplicate__get_current_user_id": 3,
            "first_active_user_query": "User.is_active + order_by id asc + first",
        },
        "fallback_patterns_after": patterns_after,
        "actor_propagation": {
            "rutas": "get_current_user_id() strict en services HTTP",
            "actuaciones_postcommit": "actor_user_id propagado desde route/service",
            "completar_trabajo": "ejecutado_por_user_id → post_commit sync",
            "notificacion_sync": "actor_user_id obligatorio",
            "relevamiento": "actor_user_id explícito en iniciador",
            "oficio": "actor_user_id explícito en iniciador",
            "cli": "--actor-user-id obligatorio",
        },
        "auth_behavior": {
            "jwt_user": "get_current_user_id() retorna identity",
            "jwt_admin1": "legítimo cuando JWT identity=1",
            "missing_jwt": "ValueError / HTTP 401",
            "invalid_identity": "ValueError, no fallback",
            "inactive_user": "ValueError, no fallback",
        },
        "tests": tests,
        "historical_policy": {"user1_refs_preserved": True},
        "sandbox_guards": {
            "user1_refs_before": user1_pre,
            "user1_refs_after": user1_post,
            "counts_before": pre,
            "counts_after": post,
            "unchanged": pre == post,
        },
        "db_writes_executed_on_sandbox": False,
        "status": "PASS" if tests["exit_code"] == 0 and guards_ok else "FAIL",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"status={report['status']} tests={tests['passed']} passed")


if __name__ == "__main__":
    main()
