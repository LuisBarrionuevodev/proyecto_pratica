#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3D — backup + apply FASE 2B (rutas + iniciadores test).
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

from app.domains.predeploy_cleanup.apply_phase2b_service import (
    apply_phase2b_routes_cleanup,
    preflight_phase2b_apply,
)
from app.domains.predeploy_cleanup.apply_service import ApplyAbortError
from app.domains.predeploy_cleanup.manifest_io import file_sha256, load_manifest, manifest_sha256

EXEC_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_execution_manifest_phase2b_routes_20260920.json"
PROTECTED_PATH = BACKEND_ROOT / "scripts" / "output" / "protected_operational_manifest_20260920.json"
STRUCTURED_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
ROUTES_DIAG = BACKEND_ROOT / "scripts" / "output" / "cleanup_phase2b_routes_initiators_diag_20260920.json"
RECONCILE = BACKEND_ROOT / "scripts" / "output" / "cleanup_phase2b_route_items_reconcile_20260920.json"
OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
BACKUP_DIR = BACKEND_ROOT.parent / "backups"

EXPECTED_EXEC_HASH = "3d89fb731c2edac5382feb254cb5c81189cf3cde4f8c2f3e60be4196c6294c96"
EXPECTED_PROT_HASH = "d8a1fda3a10e46dcdb90b22038d73e1e08c76754a59c96dc11cff4377a3b102e"
EXPECTED_SOURCE_HASHES = {
    "routes_initiators_diag": "5a6d6447f26c1360cc67474d9e9207d7b385b7a385e214cbee6ccae648607a32",
    "route_items_reconcile": "55ac856dd07813142e3d99ee5908519343c2e9d7a23bdef0953ab90b8be37ec9",
}
EXPECTED_ALEMBIC = "l7m8n9o0p1q2"
DB_NAME = "digitaliza_sandbox"
VERIFY_DB = "digitaliza_sandbox_backup_verify_phase2b"
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
        "ticket": "PREDEPLOY-CLEANUP.3D",
        "started_at": datetime.now().isoformat(),
        "writes_freeze": {
            "backend_stopped": True,
            "method": "orchestrator assumes run.py not active on digitaliza_sandbox",
            "database": DB_NAME,
        },
    }

    execution_manifest = load_manifest(EXEC_PATH)
    protected_manifest = load_manifest(PROTECTED_PATH)

    exec_hash = manifest_sha256(execution_manifest)
    execution_manifest["_source_path"] = str(EXEC_PATH)
    prot_hash = file_sha256(PROTECTED_PATH)
    routes_hash = file_sha256(ROUTES_DIAG)
    reconcile_hash = file_sha256(RECONCILE)

    if exec_hash != EXPECTED_EXEC_HASH:
        raise SystemExit(f"ABORT: exec hash {exec_hash}")
    if prot_hash != EXPECTED_PROT_HASH:
        raise SystemExit(f"ABORT: prot hash {prot_hash}")
    if routes_hash != EXPECTED_SOURCE_HASHES["routes_initiators_diag"]:
        raise SystemExit(f"ABORT: routes diag hash {routes_hash}")
    if reconcile_hash != EXPECTED_SOURCE_HASHES["route_items_reconcile"]:
        raise SystemExit(f"ABORT: reconcile hash {reconcile_hash}")

    report["manifest_hashes"] = {
        "execution": exec_hash,
        "protected": prot_hash,
        "routes_initiators_diag": routes_hash,
        "route_items_reconcile": reconcile_hash,
    }

    engine = create_engine(uri)
    with engine.connect() as conn:
        db = conn.execute(text("SELECT DATABASE()")).scalar()
        alembic = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        if db != DB_NAME or alembic != EXPECTED_ALEMBIC:
            raise SystemExit(f"ABORT: db={db} alembic={alembic}")

        baseline_checks = {
            "users": 2803,
            "establecimiento_operativo": 1657,
            "actuaciones": 8487,
            "ruta_trabajo": 3566,
            "ruta_grupo": 3737,
            "ruta_grupo_inspector": 7637,
            "ruta_item": 4551,
            "ruta_pool_dia": 714,
            "iniciador_ruta": 8563,
            "denuncia": 492,
            "relevamiento": 4592,
            "orden_trabajo": 9223,
        }
        baseline = {}
        for table, expected in baseline_checks.items():
            actual = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
            if actual != expected:
                raise SystemExit(f"ABORT baseline {table}: {actual} != {expected}")
            baseline[table] = actual
        report["baseline"] = {"database": db, "alembic": alembic, "counts": baseline}

    mysql = parse_mysql_uri(uri)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"digitaliza_sandbox_pre_cleanup_phase2b_{ts}.sql"
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
        raise SystemExit(f"ABORT mysqldump rc={proc.returncode} stderr={proc.stderr[:500]}")
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
        [
            str(MYSQL_BIN / "mysql.exe"),
            f"--host={mysql['host']}",
            f"--port={mysql['port']}",
            f"--user={mysql['user']}",
            "-e",
            admin_sql,
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    if proc_db.returncode != 0:
        raise SystemExit(f"ABORT create verify db: {proc_db.stderr}")

    with backup_path.open("r", encoding="utf-8", errors="replace") as f:
        proc_restore = subprocess.run(
            [
                str(MYSQL_BIN / "mysql.exe"),
                f"--host={mysql['host']}",
                f"--port={mysql['port']}",
                f"--user={mysql['user']}",
                VERIFY_DB,
            ],
            stdin=f,
            capture_output=True,
            text=True,
            env=env,
        )
    if proc_restore.returncode != 0:
        raise SystemExit(f"ABORT restore: {proc_restore.stderr}")

    verify_uri = re.sub(r"/[^/]+$", f"/{VERIFY_DB}", uri)
    verify_counts = {
        "ruta_item": 4551,
        "ruta_pool_dia": 714,
        "ruta_grupo": 3737,
        "ruta_trabajo": 3566,
        "iniciador_ruta": 8563,
        "actuaciones": 8487,
        "users": 2803,
    }
    with create_engine(verify_uri).connect() as vconn:
        if vconn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar() != EXPECTED_ALEMBIC:
            raise SystemExit("ABORT verify alembic")
        for table, expected in verify_counts.items():
            actual = vconn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
            if actual != expected:
                raise SystemExit(f"ABORT verify {table}: {actual} != {expected}")

    subprocess.run(
        [
            str(MYSQL_BIN / "mysql.exe"),
            f"--host={mysql['host']}",
            f"--port={mysql['port']}",
            f"--user={mysql['user']}",
            "-e",
            f"DROP DATABASE IF EXISTS `{VERIFY_DB}`;",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    report["backup_restore_verified"] = True

    with engine.connect() as conn:
        try:
            preflight = preflight_phase2b_apply(
                conn,
                execution_manifest,
                protected_manifest,
                STRUCTURED_PATH,
                confirm_database=DB_NAME,
                expected_exec_hash=EXPECTED_EXEC_HASH,
                expected_prot_hash=EXPECTED_PROT_HASH,
                expected_source_hashes=EXPECTED_SOURCE_HASHES,
                backup_confirmed=True,
            )
        except ApplyAbortError as exc:
            raise SystemExit(f"ABORT preflight: {exc}") from exc

        report["preflight"] = preflight
        print("PREFLIGHT_OK")

        try:
            apply_report = apply_phase2b_routes_cleanup(
                conn,
                execution_manifest,
                protected_manifest,
                STRUCTURED_PATH,
                confirm_database=DB_NAME,
                expected_exec_hash=EXPECTED_EXEC_HASH,
                expected_prot_hash=EXPECTED_PROT_HASH,
                expected_source_hashes=EXPECTED_SOURCE_HASHES,
                backup_path=str(backup_path),
                backup_hash=backup_hash,
                backup_size=backup_size,
                restore_verified=True,
            )
        except ApplyAbortError as exc:
            report["transaction_status"] = "ROLLED_BACK"
            report["committed"] = False
            report["writes_executed"] = False
            report["error"] = str(exc)
            out = OUTPUT_DIR / f"cleanup_phase2b_routes_apply_{ts}.json"
            out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
            raise SystemExit(f"ABORT apply: {exc}") from exc

    out = OUTPUT_DIR / f"cleanup_phase2b_routes_apply_{ts}.json"
    apply_report["backup"] = report["backup"]
    apply_report["backup_restore_verified"] = True
    apply_report["preflight_summary"] = {"status": "PREFLIGHT_OK"}
    out.write_text(json.dumps(apply_report, indent=2, default=str), encoding="utf-8")

    print(
        json.dumps(
            {
                "committed": apply_report["committed"],
                "explicit_deleted": apply_report["explicit_deleted"],
                "counts_after_routes": {
                    k: apply_report["counts_after"][k]
                    for k in (
                        "ruta_grupo_inspector",
                        "ruta_item",
                        "ruta_pool_dia",
                        "ruta_grupo",
                        "ruta_trabajo",
                        "iniciador_ruta",
                    )
                },
                "unlock": apply_report["unlock"],
                "users_fk_free": apply_report["users"]["users_test_fk_free"],
                "report": str(out),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
