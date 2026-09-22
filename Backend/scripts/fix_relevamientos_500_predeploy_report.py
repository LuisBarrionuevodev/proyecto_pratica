#!/usr/bin/env python
"""
PREDEPLOY-FIX.1 — reporte post-fix RELEVAMIENTOS-500 (read-only smoke + guards).
"""
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

OUT = BACKEND_ROOT / "scripts" / "output" / "relevamientos_500_predeploy_fix_20260920.json"


def _baseline(conn) -> dict:
    counts = {}
    for table in ("users", "relevador", "juzgado_catalogo"):
        counts[table] = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
    alembic = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
    db = conn.execute(text("SELECT DATABASE()")).scalar()
    return {
        "database": db,
        "alembic_revision": alembic,
        "counts": counts,
    }


def _smoke_qa() -> dict:
    from flask_jwt_extended import create_access_token
    from app.main import create_app
    from app.database import db

    app = create_app()
    cases = {}
    with app.app_context():
        admin_id = db.session.execute(
            text("SELECT id FROM users WHERE LOWER(username) = 'admin' LIMIT 1")
        ).scalar()
        token = create_access_token(identity=str(admin_id), additional_claims={"role": "admin"})
        headers = {"Authorization": f"Bearer {token}"}
        client = app.test_client()

        paths = [
            ("relevamientos_no_params", "/relevamientos"),
            ("relevamientos_explicit_range", "/relevamientos?desde=2026-01-01&hasta=2026-01-31"),
            ("relevamientos_future_empty", "/relevamientos?desde=2099-01-01&hasta=2099-01-31"),
            ("relevamientos_invalid_date", "/relevamientos?desde=2026-02-30"),
            ("relevamientos_desde_gt_hasta", "/relevamientos?desde=2026-05-10&hasta=2026-05-01"),
            ("profile_me", "/api/profile/me"),
            ("actuaciones_search", "/actuaciones/search?q=20&limit=5"),
            ("rutas_trabajo", "/rutas-trabajo"),
            ("denuncias", "/api/denuncias"),
            ("rubros", "/catalogos/rubros"),
        ]
        for name, path in paths:
            r = client.get(path, headers=headers)
            entry = {"path": path, "status": r.status_code}
            try:
                body = r.get_json()
                entry["json_serializable"] = True
                if name == "relevamientos_future_empty":
                    entry["items_empty"] = body.get("items") == [] if body else None
                if name == "relevamientos_no_params":
                    entry["has_items"] = "items" in (body or {})
                    entry["has_meta"] = "meta" in (body or {})
            except Exception as exc:
                entry["json_serializable"] = False
                entry["parse_error"] = str(exc)
            cases[name] = entry
    return cases


def _run_pytest() -> dict:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-o",
        "addopts=",
        "tests/test_relevamientos_list_filters_500_fix.py",
        "tests/test_rel_gestion_relevamientos_2_filters.py",
        "tests/test_phase1_jwt_guard.py",
        "-q",
        "--tb=no",
    ]
    proc = subprocess.run(cmd, cwd=BACKEND_ROOT, capture_output=True, text=True)
    passed = failed = skipped = 0
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
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
        "stdout_tail": combined[-2000:] if combined else "",
    }


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = os.getenv("SQLALCHEMY_DATABASE_URI", "").strip()
    engine = create_engine(uri)

    with engine.connect() as conn:
        baseline_pre = _baseline(conn)

    tests = _run_pytest()
    smoke = _smoke_qa()

    with engine.connect() as conn:
        baseline_post = _baseline(conn)

    guards_ok = (
        baseline_pre == baseline_post
        and baseline_post["counts"]["users"] == 1970
        and baseline_post["counts"]["relevador"] == 10
        and baseline_post["counts"]["juzgado_catalogo"] == 842
        and baseline_post["alembic_revision"] == "l7m8n9o0p1q2"
        and baseline_post["database"] == "digitaliza_sandbox"
    )

    smoke_ok = (
        smoke["relevamientos_no_params"]["status"] == 200
        and smoke["relevamientos_explicit_range"]["status"] == 200
        and smoke["relevamientos_future_empty"]["status"] == 200
        and smoke["relevamientos_invalid_date"]["status"] == 422
        and smoke["relevamientos_desde_gt_hasta"]["status"] == 422
        and smoke["profile_me"]["status"] == 200
        and smoke["actuaciones_search"]["status"] == 200
        and smoke["rutas_trabajo"]["status"] == 200
        and smoke["denuncias"]["status"] == 200
        and smoke["rubros"]["status"] == 200
    )

    status = "PASS" if tests["exit_code"] == 0 and smoke_ok and guards_ok else "FAIL"

    report = {
        "generated_at": datetime.now().isoformat(),
        "ticket": "PREDEPLOY-FIX.1",
        "mode": "FIX_REPORT",
        "files_changed": [
            "app/domains/relevamientos/schemas/list_filters.py",
            "app/domains/relevamientos/routes/list.py",
            "app/domains/relevamientos/routes/list_operativa.py",
            "tests/test_relevamientos_list_filters_500_fix.py",
        ],
        "functions_changed": [
            "RelevamientosListFilters.apply_defaults_and_validate_range",
            "listar_relevamientos",
            "listar_relevamientos_gestion_operativa",
        ],
        "root_cause_reference": "scripts/output/relevamientos_500_predeploy_diag_20260920.json",
        "date_fix": {
            "before": "date(next_month.year, next_month.month, next_month.day - 1)",
            "after": "next_month - timedelta(days=1)",
            "file": "app/domains/relevamientos/schemas/list_filters.py",
        },
        "validation_error_fix": {
            "before": "jsonify({..., 'errors': e.errors()})",
            "after": "jsonify({..., 'errors': pydantic_errors_to_cell_map(e)})",
            "helper": "app.shared.errors.pydantic_errors_to_cell_map",
            "pattern_source": ["/actuaciones/search", "/api/denuncias"],
        },
        "list_operativa_changed": True,
        "tests": tests,
        "smoke_qa": smoke,
        "cleanup_guards": {
            "baseline_pre": baseline_pre,
            "baseline_post": baseline_post,
            "unchanged": baseline_pre == baseline_post,
            "expected": {
                "users": 1970,
                "relevador": 10,
                "juzgado_catalogo": 842,
                "alembic_revision": "l7m8n9o0p1q2",
                "database": "digitaliza_sandbox",
            },
        },
        "db_writes_executed": False,
        "status": status,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"status={status}")
    print(f"tests exit={tests['exit_code']} passed={tests['passed']}")


if __name__ == "__main__":
    main()
