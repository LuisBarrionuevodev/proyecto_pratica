#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3B — backup + apply FASE 2A (solo establecimiento_operativo).
"""
from __future__ import annotations

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

from app.domains.predeploy_cleanup.apply_phase2a_service import (
    apply_phase2a_eo_cleanup,
    load_acts_274,
    post_commit_user_analysis,
    preflight_phase2a_apply,
)
from app.domains.predeploy_cleanup.apply_service import ApplyAbortError
from app.domains.predeploy_cleanup.manifest_io import file_sha256, load_manifest, manifest_sha256

EXEC_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_execution_manifest_phase2a_eo_20260920.json"
PROTECTED_PATH = BACKEND_ROOT / "scripts" / "output" / "protected_operational_manifest_20260920.json"
STRUCTURED_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
BACKUP_DIR = BACKEND_ROOT.parent / "backups"

EXPECTED_EXEC_HASH = "fba649c7861eabf7eec4e7d3d0cfb47c88e07e054b73882e29f2705fc61c0e24"
EXPECTED_PROT_HASH = "d8a1fda3a10e46dcdb90b22038d73e1e08c76754a59c96dc11cff4377a3b102e"
EXPECTED_ALEMBIC = "l7m8n9o0p1q2"
DB_NAME = "digitaliza_sandbox"
VERIFY_DB = "digitaliza_sandbox_backup_verify_phase2a"
MYSQL_BIN = Path(os.getenv("MYSQL_BIN", r"C:\Program Files\MySQL\MySQL Server 8.0\bin"))


def parse_mysql_uri(uri: str) -> dict:
    parsed = urlparse(uri.replace("+pymysql", ""))
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": (parsed.path or "").lstrip("/"),
    }


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = os.getenv("SQLALCHEMY_DATABASE_URI", "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report: dict = {
        "ticket": "PREDEPLOY-CLEANUP.3B",
        "started_at": datetime.now().isoformat(),
        "writes_freeze": {
            "backend_stopped": True,
            "note": "apply orchestrator; verificar run.py no activo",
        },
    }

    execution_manifest = load_manifest(EXEC_PATH)
    protected_manifest = load_manifest(PROTECTED_PATH)
    acts_274 = load_acts_274(STRUCTURED_PATH)

    exec_hash = manifest_sha256(execution_manifest)
    prot_hash = file_sha256(PROTECTED_PATH)
    if exec_hash != EXPECTED_EXEC_HASH:
        raise SystemExit(f"ABORT: exec hash {exec_hash}")
    if prot_hash != EXPECTED_PROT_HASH:
        raise SystemExit(f"ABORT: prot hash {prot_hash}")

    report["manifest_hashes"] = {
        "execution": exec_hash,
        "protected": prot_hash,
    }

    engine = create_engine(uri)
    with engine.connect() as conn:
        db = conn.execute(text("SELECT DATABASE()")).scalar()
        alembic = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        if db != DB_NAME or alembic != EXPECTED_ALEMBIC:
            raise SystemExit(f"ABORT: db={db} alembic={alembic}")
        eo_cnt = conn.execute(text("SELECT COUNT(*) FROM establecimiento_operativo")).scalar()
        act_cnt = conn.execute(text("SELECT COUNT(*) FROM actuaciones")).scalar()
        usr_cnt = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        if (eo_cnt, act_cnt, usr_cnt) != (2057, 8487, 2803):
            raise SystemExit(f"ABORT: baseline eo={eo_cnt} act={act_cnt} users={usr_cnt}")
        report["baseline"] = {
            "database": db,
            "alembic": alembic,
            "establecimiento_operativo": eo_cnt,
            "actuaciones": act_cnt,
            "users": usr_cnt,
        }

    mysql = parse_mysql_uri(uri)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"digitaliza_sandbox_pre_cleanup_phase2a_eo_{ts}.sql"
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

    print(f"Backup: {backup_path}")
    with backup_path.open("w", encoding="utf-8", newline="\n") as f:
        proc = subprocess.run(dump_cmd, stdout=f, stderr=subprocess.PIPE, text=True, env=env)
    backup_size = backup_path.stat().st_size
    backup_hash = file_sha256(backup_path)
    if proc.returncode != 0 or backup_size == 0:
        raise SystemExit(f"ABORT mysqldump rc={proc.returncode}")
    report["backup"] = {
        "path": str(backup_path),
        "size": backup_size,
        "sha256": backup_hash,
        "exit_code": proc.returncode,
        "timestamp": datetime.now().isoformat(),
    }

    admin_sql = (
        f"DROP DATABASE IF EXISTS `{VERIFY_DB}`; "
        f"CREATE DATABASE `{VERIFY_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    )
    proc_db = subprocess.run(
        [str(MYSQL_BIN / "mysql.exe"), f"--host={mysql['host']}", f"--port={mysql['port']}",
         f"--user={mysql['user']}", "-e", admin_sql],
        capture_output=True, text=True, env=env,
    )
    if proc_db.returncode != 0:
        raise SystemExit(f"ABORT create verify db: {proc_db.stderr}")

    with backup_path.open("r", encoding="utf-8", errors="replace") as f:
        proc_restore = subprocess.run(
            [str(MYSQL_BIN / "mysql.exe"), f"--host={mysql['host']}", f"--port={mysql['port']}",
             f"--user={mysql['user']}", VERIFY_DB],
            stdin=f, capture_output=True, text=True, env=env,
        )
    if proc_restore.returncode != 0:
        raise SystemExit(f"ABORT restore: {proc_restore.stderr}")

    verify_uri = re.sub(r"/[^/]+$", f"/{VERIFY_DB}", uri)
    with create_engine(verify_uri).connect() as vconn:
        if vconn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar() != EXPECTED_ALEMBIC:
            raise SystemExit("ABORT verify alembic")
        if vconn.execute(text("SELECT COUNT(*) FROM establecimiento_operativo")).scalar() != 2057:
            raise SystemExit("ABORT verify eo count")
    subprocess.run(
        [str(MYSQL_BIN / "mysql.exe"), f"--host={mysql['host']}", f"--port={mysql['port']}",
         f"--user={mysql['user']}", "-e", f"DROP DATABASE IF EXISTS `{VERIFY_DB}`;"],
        capture_output=True, text=True, env=env,
    )
    report["backup_restore_verified"] = True

    with engine.connect() as conn:
        try:
            preflight = preflight_phase2a_apply(
                conn, execution_manifest, protected_manifest, acts_274,
                confirm_database=DB_NAME,
                expected_exec_hash=EXPECTED_EXEC_HASH,
                expected_prot_hash=EXPECTED_PROT_HASH,
                backup_confirmed=True,
            )
        except ApplyAbortError as exc:
            raise SystemExit(f"ABORT preflight: {exc}") from exc
        report["preflight"] = preflight
        report["transaction_started"] = datetime.now().isoformat()

        try:
            apply_report = apply_phase2a_eo_cleanup(
                conn,
                execution_manifest,
                protected_manifest,
                acts_274,
                confirm_database=DB_NAME,
                expected_exec_hash=EXPECTED_EXEC_HASH,
                expected_prot_hash=EXPECTED_PROT_HASH,
                backup_path=str(backup_path),
                backup_hash=backup_hash,
                backup_size=backup_size,
                structured_acts_diag=STRUCTURED_PATH,
            )
        except ApplyAbortError as exc:
            report["transaction_status"] = "ROLLED_BACK"
            report["error"] = str(exc)
            out = OUTPUT_DIR / f"cleanup_phase2a_eo_apply_{ts}.json"
            out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
            raise SystemExit(f"ABORT apply: {exc}") from exc

        apply_report["post_commit_users"] = post_commit_user_analysis(conn)
        apply_report["backup"] = report["backup"]
        apply_report["preflight"] = preflight

    out = OUTPUT_DIR / f"cleanup_phase2a_eo_apply_{ts}.json"
    out.write_text(json.dumps(apply_report, indent=2, default=str), encoding="utf-8")
    report["apply_report_path"] = str(out)
    report["finished_at"] = datetime.now().isoformat()
    print(json.dumps({
        "committed": apply_report["committed"],
        "eo_after": apply_report["counts_after"]["establecimiento_operativo"],
        "users_unlocked": apply_report["post_commit_users"]["UNLOCKED_FOR_PHASE2D_count"],
        "report": str(out),
    }, indent=2))


if __name__ == "__main__":
    main()
