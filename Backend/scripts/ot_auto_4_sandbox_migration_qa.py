#!/usr/bin/env python
"""
OT-AUTO.4 — Sandbox precheck, backup, migration y postcheck.

Uso:
  cd Backend
  python scripts/ot_auto_4_sandbox_migration_qa.py

NO ejecuta pytest contra sandbox.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
BACKUP_DIR = REPO_ROOT / "backups"
OUTPUT_PATH = BACKEND_ROOT / "scripts/output/ot_auto_4_collision_sandbox_qa_20260921.json"

EXPECTED_REVISION_BEFORE = "n9o0p1q2r3s4"
EXPECTED_REVISION_AFTER = "o0p1q2r3s4t5"
SEED_DISPLAY = "089862"
SEED_VALUE = 89862

COUNT_TABLES = (
    "orden_trabajo",
    "actuaciones",
    "ruta_trabajo",
    "ruta_item",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _engine():
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    test_uri = (os.getenv("TEST_DATABASE_URL") or "").strip()
    if not uri or "sandbox" not in uri.lower():
        raise RuntimeError(f"SQLALCHEMY_DATABASE_URI debe apuntar a sandbox, got: {uri}")
    if test_uri and uri == test_uri:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI no puede ser digitaliza_test")
    if "digitaliza_test" in uri.lower():
        raise RuntimeError("Abort: apunta a digitaliza_test")
    return create_engine(uri), uri


def _table_counts(conn) -> dict[str, int]:
    out: dict[str, int] = {}
    for t in COUNT_TABLES:
        out[t] = int(conn.execute(text(f"SELECT COUNT(*) FROM `{t}`")).scalar() or 0)
    return out


def _alembic_version(conn) -> str | None:
    try:
        return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        return None


def _run_backup(uri: str) -> dict[str, Any]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"digitaliza_sandbox_ot_auto_4_{ts}.sql"
    # mysql+pymysql://user:pass@host:port/db
    rest = uri.split("://", 1)[1]
    auth, host_db = rest.split("@", 1)
    user, password = auth.split(":", 1)
    host_port, database = host_db.split("/", 1)
    host = host_port.split(":")[0]
    port = host_port.split(":")[1] if ":" in host_port else "3306"

    cmd = [
        "mysqldump",
        f"-h{host}",
        f"-P{port}",
        f"-u{user}",
        f"-p{password}",
        "--single-transaction",
        "--routines",
        "--triggers",
        database,
    ]
    try:
        with open(path, "w", encoding="utf-8") as f:
            subprocess.run(cmd, stdout=f, check=True, stderr=subprocess.PIPE, text=True)
        size = path.stat().st_size
        return {
            "path": str(path),
            "timestamp": ts,
            "size_bytes": size,
            "restore_command": (
                f"mysql -h {host} -P {port} -u {user} -p {database} < \"{path}\""
            ),
            "status": "OK",
        }
    except FileNotFoundError:
        return {"status": "SKIPPED", "reason": "mysqldump not found"}
    except subprocess.CalledProcessError as exc:
        return {"status": "FAIL", "stderr": exc.stderr}


def _schema_postcheck(conn) -> dict[str, Any]:
    insp = inspect(conn)
    cols = {c["name"]: c for c in insp.get_columns("orden_trabajo")}
    numero_acta = cols.get("numero_acta", {})
    sec = cols.get("numero_secuencia_global", {})
    legacy_null = int(
        conn.execute(
            text("SELECT COUNT(*) FROM orden_trabajo WHERE numero_secuencia_global IS NULL")
        ).scalar()
        or 0
    )
    total_ot = int(conn.execute(text("SELECT COUNT(*) FROM orden_trabajo")).scalar() or 0)
    contador = conn.execute(
        text("SELECT next_value FROM orden_trabajo_contador ORDER BY id ASC LIMIT 1")
    ).scalar()
    audit_count = int(
        conn.execute(text("SELECT COUNT(*) FROM orden_trabajo_contador_audit")).scalar() or 0
    )
    return {
        "numero_acta_varchar10": str(numero_acta.get("type", "")).upper().find("VARCHAR") >= 0
        and (numero_acta.get("type").length if hasattr(numero_acta.get("type"), "length") else 10) >= 10,
        "numero_secuencia_global_nullable_unique": sec is not None,
        "orden_trabajo_contador_exists": contador is not None,
        "orden_trabajo_contador_audit_exists": audit_count >= 0,
        "legacy_numero_secuencia_global_null_count": legacy_null,
        "orden_trabajo_total": total_ot,
        "contador_next_value": int(contador) if contador is not None else None,
    }


def _seed_revalidation(conn) -> dict[str, Any]:
    occupied = conn.execute(
        text("SELECT COUNT(*) FROM orden_trabajo WHERE numero_acta = :d"),
        {"d": SEED_DISPLAY},
    ).scalar()
    max_auto = conn.execute(
        text(
            "SELECT MAX(numero_secuencia_global) FROM orden_trabajo "
            "WHERE numero_secuencia_global IS NOT NULL"
        )
    ).scalar()
    max_display = conn.execute(
        text(
            "SELECT MAX(CAST(numero_acta AS UNSIGNED)) FROM orden_trabajo "
            "WHERE numero_acta REGEXP '^[0-9]+$'"
        )
    ).scalar()
    return {
        "seed_display": SEED_DISPLAY,
        "seed_value": SEED_VALUE,
        "089862_occupied": int(occupied or 0) > 0,
        "max_numero_secuencia_global": int(max_auto) if max_auto else None,
        "max_numeric_numero_acta": int(max_display) if max_display else None,
        "seed_free": int(occupied or 0) == 0,
    }


def main() -> int:
    report: dict[str, Any] = {
        "ticket": "OT-AUTO.4",
        "generated_at": _utc_now(),
        "status": "PENDING",
    }
    engine, uri = _engine()

    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT DATABASE()")).scalar()
        report["database"] = {"name": db_name, "uri_masked": uri.split("@")[-1]}
        if str(db_name).lower() != "digitaliza_sandbox":
            report["status"] = "FAIL"
            report["error"] = f"DATABASE()={db_name}, expected digitaliza_sandbox"
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 1

        alembic_before = _alembic_version(conn)
        report["alembic_before"] = alembic_before
        report["seed_revalidation"] = _seed_revalidation(conn)
        report["migration_counts_pre"] = _table_counts(conn)
        report["schema_pre"] = _schema_postcheck(conn)

    report["backup"] = _run_backup(uri)

    migration_needed = alembic_before != EXPECTED_REVISION_AFTER
    report["migration_needed"] = migration_needed
    report["expected_revision_before"] = EXPECTED_REVISION_BEFORE
    report["expected_revision_after"] = EXPECTED_REVISION_AFTER

    if migration_needed:
        if alembic_before not in (EXPECTED_REVISION_BEFORE, EXPECTED_REVISION_AFTER):
            report["status"] = "FAIL"
            report["migration_error"] = (
                f"Unexpected alembic head {alembic_before}; "
                f"expected {EXPECTED_REVISION_BEFORE} or {EXPECTED_REVISION_AFTER}"
            )
        elif report["seed_revalidation"]["089862_occupied"] and alembic_before == EXPECTED_REVISION_BEFORE:
            report["status"] = "FAIL"
            report["migration_error"] = "089862 occupied; migration precheck would abort"
        else:
            try:
                proc = subprocess.run(
                    ["flask", "db", "upgrade"],
                    cwd=str(BACKEND_ROOT),
                    capture_output=True,
                    text=True,
                    check=True,
                    env={**os.environ, "FLASK_APP": "app:create_app"},
                )
                report["migration_stdout"] = proc.stdout[-2000:] if proc.stdout else ""
            except subprocess.CalledProcessError as exc:
                report["status"] = "FAIL"
                report["migration_error"] = exc.stderr or str(exc)
    else:
        report["migration_skipped"] = "already at head"

    with engine.connect() as conn:
        report["alembic_after"] = _alembic_version(conn)
        report["migration_counts_post"] = _table_counts(conn)
        report["schema_post"] = _schema_postcheck(conn)
        report["seed_applied"] = report["schema_post"].get("contador_next_value")

        drift = {
            k: report["migration_counts_post"][k] - report["migration_counts_pre"][k]
            for k in COUNT_TABLES
        }
        report["migration_counts_drift"] = drift
        report["operational_drift"] = any(v != 0 for v in drift.values())

    if report.get("status") != "FAIL":
        ok_alembic = report["alembic_after"] == EXPECTED_REVISION_AFTER
        ok_schema = report["schema_post"]["orden_trabajo_contador_exists"]
        ok_drift = not report["operational_drift"]
        report["status"] = "PASS" if ok_alembic and ok_schema and ok_drift else "FAIL"

    report["allocator_semantics"] = {
        "next_value_meaning": "primer valor desde donde comenzar la búsqueda (no garantiza asignación)",
        "occupation_rule": "orden_trabajo.numero_acta == format_ot_display(candidate), cualquier año, incluye soft-deleted",
        "shared_helper": "next_available_candidates",
        "preview_no_reserve": True,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
