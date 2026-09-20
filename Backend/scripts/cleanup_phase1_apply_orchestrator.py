#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.2C — backup verificado + apply FASE 1 + validación post-cleanup.

Ejecuta prechecks, backup mysqldump, restore de verificación, apply y reporte.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from app.domains.predeploy_cleanup.apply_service import (
    ApplyAbortError,
    apply_phase1_cleanup,
    preflight_apply,
)
from app.domains.predeploy_cleanup.execution_manifest import load_execution_sets, verify_manifest_hash
from app.domains.predeploy_cleanup.manifest_io import file_sha256, load_manifest, validate_ids_exist
from app.domains.predeploy_cleanup.sequential_simulator import _table_for_entity

EXEC_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_execution_manifest_phase1_20260920.json"
PROTECTED_PATH = BACKEND_ROOT / "scripts" / "output" / "protected_operational_manifest_20260920.json"
XLSX_PATH = BACKEND_ROOT / "docs" / "Listado_OT_Notificacion_Inspeccion_Comprobacion_Oficio.xlsx"
OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
BACKUP_DIR = BACKEND_ROOT.parent / "backups"

EXPECTED_EXEC_HASH = "27937c65ba75748b8324964185118b091a83c15bb3c988eee958f2a15d3537f8"
EXPECTED_PROT_HASH = "c3db321750eb962ad4d2eea66b0ce59b8b84426445b64f62f6348f41bd08f518"
EXPECTED_XLSX_HASH = "e0345f6b9452812ddc3abd20b02145152e83ff738455a0540ca3e22790f38668"
EXPECTED_ALEMBIC = "l7m8n9o0p1q2"
DB_NAME = "digitaliza_sandbox"
VERIFY_DB = "digitaliza_sandbox_backup_verify"
MYSQL_BIN = Path(
    os.getenv("MYSQL_BIN", r"C:\Program Files\MySQL\MySQL Server 8.0\bin")
)

BASELINE = {
    "actuaciones": 8890,
    "ruta_trabajo": 6614,
    "ruta_item": 6821,
    "iniciador_ruta": 10282,
    "denuncia": 518,
    "relevamiento": 4618,
    "orden_trabajo": 9642,
    "users": 4149,
}


def parse_mysql_uri(uri: str) -> dict[str, str | int]:
    """Extrae host, port, user, password, database de SQLAlchemy URI."""
    parsed = urlparse(uri.replace("+pymysql", ""))
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": (parsed.path or "").lstrip("/"),
    }


def count_baseline(conn) -> dict[str, int]:
    counts = {}
    for entity, _expected in BASELINE.items():
        table = _table_for_entity(entity)
        counts[entity] = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar() or 0
    return counts


def verify_execution_ids(conn, execution_manifest: dict) -> None:
    execution_ids = load_execution_sets(execution_manifest)
    missing_all: list[dict] = []
    for entity, ids in execution_ids.items():
        if not ids:
            continue
        table = _table_for_entity(entity)
        missing = validate_ids_exist(conn, table, ids, label=entity)
        if missing:
            missing_all.extend(missing[:3])
    if missing_all:
        raise SystemExit(f"ABORT: execution IDs missing: {missing_all[:10]}")


def run_mysql_cmd(args: list[str], *, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, env=env)


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = os.getenv("SQLALCHEMY_DATABASE_URI", "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    report: dict = {
        "ticket": "PREDEPLOY-CLEANUP.2C",
        "started_at": datetime.now().isoformat(),
        "writes_freeze": {
            "backend_stopped": True,
            "note": "run.py no activo; frontend puede seguir sin escribir en sandbox",
        },
    }

    execution_manifest = load_manifest(EXEC_PATH)
    protected_manifest = load_manifest(PROTECTED_PATH)

    if not verify_manifest_hash(execution_manifest):
        raise SystemExit("ABORT: execution manifest hash mismatch")
    if execution_manifest.get("execution_manifest_hash") != EXPECTED_EXEC_HASH:
        raise SystemExit("ABORT: execution manifest hash != expected")
    prot_hash = protected_manifest.get("manifest_sha256") or file_sha256(PROTECTED_PATH)
    if prot_hash != EXPECTED_PROT_HASH:
        raise SystemExit(f"ABORT: protected hash {prot_hash} != {EXPECTED_PROT_HASH}")
    if XLSX_PATH.is_file():
        xlsx_hash = file_sha256(XLSX_PATH)
        if xlsx_hash != EXPECTED_XLSX_HASH:
            raise SystemExit(f"ABORT: xlsx hash {xlsx_hash} != {EXPECTED_XLSX_HASH}")
    report["manifest_hashes"] = {
        "execution": EXPECTED_EXEC_HASH,
        "protected": EXPECTED_PROT_HASH,
        "xlsx": EXPECTED_XLSX_HASH,
    }

    engine = create_engine(uri)
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT DATABASE()")).scalar()
        if db_name != DB_NAME:
            raise SystemExit(f"ABORT: DATABASE()={db_name}")
        alembic = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        if alembic != EXPECTED_ALEMBIC:
            raise SystemExit(f"ABORT: alembic={alembic}")
        counts = count_baseline(conn)
        for k, v in BASELINE.items():
            if counts[k] != v:
                raise SystemExit(f"ABORT: baseline {k} db={counts[k]} expected={v}")
        report["precheck"] = {"database": db_name, "alembic": alembic, "baseline": counts}
        verify_execution_ids(conn, execution_manifest)
        blocked = execution_manifest.get("blocked_preserve", {})
        execution_ids = load_execution_sets(execution_manifest)
        for entity in ("actuaciones", "iniciador_ruta", "relevamiento", "denuncia", "orden_trabajo", "users"):
            blocked_ids = set(blocked.get(entity, []))
            inter = blocked_ids & execution_ids.get(entity, set())
            if inter:
                raise SystemExit(f"ABORT: blocked∩execution {entity}: {len(inter)}")

    mysql = parse_mysql_uri(uri)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"digitaliza_sandbox_pre_cleanup_phase1_{ts}.sql"

    dump_cmd = [
        str(MYSQL_BIN / "mysqldump.exe"),
        f"--host={mysql['host']}",
        f"--port={mysql['port']}",
        f"--user={mysql['user']}",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--set-gtid-purged=OFF",
        DB_NAME,
    ]
    env = os.environ.copy()
    if mysql["password"]:
        env["MYSQL_PWD"] = str(mysql["password"])

    print(f"Creating backup: {backup_path}")
    with backup_path.open("w", encoding="utf-8", newline="\n") as f:
        proc = subprocess.run(dump_cmd, stdout=f, stderr=subprocess.PIPE, text=True, env=env)
    backup_size = backup_path.stat().st_size
    backup_hash = file_sha256(backup_path)
    if proc.returncode != 0 or backup_size == 0:
        raise SystemExit(f"ABORT: mysqldump failed rc={proc.returncode} stderr={proc.stderr}")
    report["backup"] = {
        "path": str(backup_path),
        "size": backup_size,
        "sha256": backup_hash,
        "exit_code": proc.returncode,
        "timestamp": datetime.now().isoformat(),
    }

    admin_args = [
        str(MYSQL_BIN / "mysql.exe"),
        f"--host={mysql['host']}",
        f"--port={mysql['port']}",
        f"--user={mysql['user']}",
        "-e",
        f"DROP DATABASE IF EXISTS `{VERIFY_DB}`; CREATE DATABASE `{VERIFY_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
    ]
    proc_drop = run_mysql_cmd(admin_args, env=env)
    if proc_drop.returncode != 0:
        raise SystemExit(f"ABORT: create verify db failed: {proc_drop.stderr}")

    restore_cmd = [
        str(MYSQL_BIN / "mysql.exe"),
        f"--host={mysql['host']}",
        f"--port={mysql['port']}",
        f"--user={mysql['user']}",
        VERIFY_DB,
    ]
    with backup_path.open("r", encoding="utf-8", errors="replace") as f:
        proc_restore = subprocess.run(restore_cmd, stdin=f, capture_output=True, text=True, env=env)
    if proc_restore.returncode != 0:
        raise SystemExit(f"ABORT: restore failed: {proc_restore.stderr}")

    verify_uri = re.sub(r"/[^/]+$", f"/{VERIFY_DB}", uri)
    verify_engine = create_engine(verify_uri)
    with verify_engine.connect() as vconn:
        val = vconn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        if val != EXPECTED_ALEMBIC:
            raise SystemExit(f"ABORT: verify db alembic={val}")
        vcounts = count_baseline(vconn)
        for k, v in BASELINE.items():
            if vcounts[k] != v:
                raise SystemExit(f"ABORT: verify restore {k}={vcounts[k]} expected={v}")
    report["backup_restore_verified"] = True

    drop_verify_cmd = [
        str(MYSQL_BIN / "mysql.exe"),
        f"--host={mysql['host']}",
        f"--port={mysql['port']}",
        f"--user={mysql['user']}",
        "-e",
        f"DROP DATABASE IF EXISTS `{VERIFY_DB}`;",
    ]
    proc_drop2 = run_mysql_cmd(drop_verify_cmd, env=env)
    report["verify_db_dropped"] = proc_drop2.returncode == 0

    with engine.connect() as conn:
        try:
            preflight = preflight_apply(
                conn,
                execution_manifest,
                protected_manifest,
                confirm_database=DB_NAME,
                backup_confirmed=True,
            )
        except ApplyAbortError as exc:
            raise SystemExit(f"ABORT preflight: {exc}") from exc
        report["preflight"] = preflight
        report["transaction_started"] = datetime.now().isoformat()

        try:
            apply_report = apply_phase1_cleanup(
                conn,
                execution_manifest,
                protected_manifest,
                confirm_database=DB_NAME,
                backup_path=str(backup_path),
                backup_size=backup_size,
                backup_hash=backup_hash,
            )
        except ApplyAbortError as exc:
            report["transaction_status"] = "ROLLED_BACK"
            report["error"] = str(exc)
            out = OUTPUT_DIR / f"cleanup_phase1_apply_{ts}.json"
            out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
            raise SystemExit(f"ABORT apply: {exc}") from exc

    apply_report["backup"] = report["backup"]
    apply_report["preflight"] = preflight
    apply_report["backup_restore_verified"] = True
    out = OUTPUT_DIR / f"cleanup_phase1_apply_{ts}.json"
    out.write_text(json.dumps(apply_report, indent=2, default=str), encoding="utf-8")
    report["apply_report_path"] = str(out)
    report["apply"] = apply_report
    report["finished_at"] = datetime.now().isoformat()

    summary_path = OUTPUT_DIR / f"cleanup_phase1_apply_summary_{ts}.json"
    summary_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"committed": apply_report["committed"], "report": str(out)}, indent=2))


if __name__ == "__main__":
    main()
