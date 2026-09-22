#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3G.2 — backup + apply FASE 2C.2B (110 act + 26 rel + 110 OT).
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

from app.domains.predeploy_cleanup.apply_phase2c2b_service import (
    EXPECTED_CASCADE_RECONCILE_HASH,
    EXPECTED_EXEC_HASH,
    EXPECTED_PROT_HASH,
    EXPECTED_SOURCE_DIAG_HASH,
    apply_phase2c2b_sources_cleanup,
    preflight_phase2c2b_apply,
)
from app.domains.predeploy_cleanup.apply_service import ApplyAbortError
from app.domains.predeploy_cleanup.manifest_io import file_sha256, load_manifest, manifest_sha256

EXEC_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_execution_manifest_phase2c2b_sources_20260920.json"
SOURCES_DIAG_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_phase2c2b_sources_diag_20260920.json"
CASCADE_RECONCILE_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_phase2c2b_cascade_reconcile_20260920.json"
PROTECTED_PATH = BACKEND_ROOT / "scripts" / "output" / "protected_operational_manifest_20260920.json"
NOTIF_SOURCE_DIAG_PATH = (
    BACKEND_ROOT / "scripts" / "output" / "cleanup_phase2c2_notification_source_diag_20260920.json"
)
RESIDUAL_GRAPH_DIAG_PATH = (
    BACKEND_ROOT / "scripts" / "output" / "cleanup_phase2c2_residual_graph_diag_20260920.json"
)
OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
BACKUP_DIR = BACKEND_ROOT.parent / "backups"

EXPECTED_ALEMBIC = "l7m8n9o0p1q2"
DB_NAME = "digitaliza_sandbox"
VERIFY_DB = "digitaliza_sandbox_backup_verify_phase2c2b"
MYSQL_BIN = Path(os.getenv("MYSQL_BIN", r"C:\Program Files\MySQL\MySQL Server 8.0\bin"))
FREEZE_METHOD = "backend_development_stopped_during_backup_preflight_transaction_postconditions"

BASELINE_CHECKS = {
    "users": 2803,
    "establecimiento_operativo": 1657,
    "ruta_trabajo": 2715,
    "ruta_grupo": 2884,
    "ruta_grupo_inspector": 5931,
    "ruta_item": 3697,
    "ruta_pool_dia": 361,
    "iniciador_ruta": 8039,
    "actuaciones": 8222,
    "denuncia": 417,
    "relevamiento": 4592,
    "orden_trabajo": 8958,
    "inspeccion": 915,
    "actuaciones_inspector": 4189,
    "acta_inspeccion_item": 52,
    "clausura": 69,
    "decomiso": 25,
    "relevamiento_relevador": 535,
}


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
        "ticket": "PREDEPLOY-CLEANUP.3G.2",
        "started_at": datetime.now().isoformat(),
        "writes_freeze": {
            "backend_stopped": True,
            "method": FREEZE_METHOD,
            "database": DB_NAME,
        },
    }

    for p in (EXEC_PATH, SOURCES_DIAG_PATH, CASCADE_RECONCILE_PATH, PROTECTED_PATH):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    execution_manifest = load_manifest(EXEC_PATH)
    protected_manifest = load_manifest(PROTECTED_PATH)
    exec_hash = manifest_sha256(execution_manifest)
    execution_manifest["_source_path"] = str(EXEC_PATH)
    source_diag_hash = file_sha256(SOURCES_DIAG_PATH)
    cascade_hash = file_sha256(CASCADE_RECONCILE_PATH)
    prot_hash = file_sha256(PROTECTED_PATH)

    if exec_hash != EXPECTED_EXEC_HASH:
        raise SystemExit(f"ABORT: exec hash {exec_hash} != {EXPECTED_EXEC_HASH}")
    if source_diag_hash != EXPECTED_SOURCE_DIAG_HASH:
        raise SystemExit(f"ABORT: source diag hash {source_diag_hash}")
    if cascade_hash != EXPECTED_CASCADE_RECONCILE_HASH:
        raise SystemExit(f"ABORT: cascade reconcile hash {cascade_hash}")
    if prot_hash != EXPECTED_PROT_HASH:
        raise SystemExit(f"ABORT: protected hash {prot_hash}")

    report["manifest_hashes"] = {
        "execution": exec_hash,
        "source_diag": source_diag_hash,
        "cascade_reconcile": cascade_hash,
        "protected": prot_hash,
    }

    engine = create_engine(uri)
    with engine.connect() as conn:
        db = conn.execute(text("SELECT DATABASE()")).scalar()
        alembic = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        if db != DB_NAME or alembic != EXPECTED_ALEMBIC:
            raise SystemExit(f"ABORT: db={db} alembic={alembic}")
        baseline = {}
        for table, expected in BASELINE_CHECKS.items():
            actual = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
            if actual != expected:
                raise SystemExit(f"ABORT baseline {table}: {actual} != {expected}")
            baseline[table] = actual
        report["baseline"] = {"database": db, "alembic": alembic, "counts": baseline}

    mysql = parse_mysql_uri(uri)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"digitaliza_sandbox_pre_cleanup_phase2c2b_{ts}.sql"
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
        raise SystemExit(f"ABORT restore: {proc_restore.stderr[:500]}")

    verify_counts = {
        "actuaciones": 8222,
        "relevamiento": 4592,
        "orden_trabajo": 8958,
        "inspeccion": 915,
        "actuaciones_inspector": 4189,
        "relevamiento_relevador": 535,
        "users": 2803,
    }
    verify_uri = re.sub(r"/[^/]+$", f"/{VERIFY_DB}", uri)
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
    report["restore_verify"] = {"verified": True, "verify_db": VERIFY_DB}

    with engine.connect() as conn:
        try:
            preflight = preflight_phase2c2b_apply(
                conn,
                execution_manifest,
                protected_manifest,
                SOURCES_DIAG_PATH,
                CASCADE_RECONCILE_PATH,
                notif_source_diag_path=NOTIF_SOURCE_DIAG_PATH,
                residual_graph_diag_path=RESIDUAL_GRAPH_DIAG_PATH,
                confirm_database=DB_NAME,
                expected_exec_hash=EXPECTED_EXEC_HASH,
                expected_source_diag_hash=EXPECTED_SOURCE_DIAG_HASH,
                expected_cascade_hash=EXPECTED_CASCADE_RECONCILE_HASH,
                expected_prot_hash=EXPECTED_PROT_HASH,
                backup_confirmed=True,
            )
        except ApplyAbortError as exc:
            raise SystemExit(f"ABORT preflight: {exc}") from exc

        report["preflight"] = preflight
        print("PREFLIGHT_OK")

        try:
            apply_report = apply_phase2c2b_sources_cleanup(
                conn,
                execution_manifest,
                protected_manifest,
                SOURCES_DIAG_PATH,
                CASCADE_RECONCILE_PATH,
                notif_source_diag_path=NOTIF_SOURCE_DIAG_PATH,
                residual_graph_diag_path=RESIDUAL_GRAPH_DIAG_PATH,
                confirm_database=DB_NAME,
                expected_exec_hash=EXPECTED_EXEC_HASH,
                expected_source_diag_hash=EXPECTED_SOURCE_DIAG_HASH,
                expected_cascade_hash=EXPECTED_CASCADE_RECONCILE_HASH,
                expected_prot_hash=EXPECTED_PROT_HASH,
                backup_path=str(backup_path),
                backup_hash=backup_hash,
                backup_size=backup_size,
                restore_verified=True,
                freeze_method=FREEZE_METHOD,
            )
        except ApplyAbortError as exc:
            report["transaction_status"] = "ROLLED_BACK"
            report["committed"] = False
            report["writes_executed"] = False
            report["error"] = str(exc)
            out = OUTPUT_DIR / f"cleanup_phase2c2b_sources_apply_{ts}.json"
            out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
            raise SystemExit(f"ABORT apply: {exc}") from exc

    out = OUTPUT_DIR / f"cleanup_phase2c2b_sources_apply_{ts}.json"
    apply_report["backup"] = report["backup"]
    apply_report["restore_verify"] = report["restore_verify"]
    apply_report["preflight_summary"] = {"status": "PREFLIGHT_OK"}
    out.write_text(json.dumps(apply_report, indent=2, default=str), encoding="utf-8")

    print(
        json.dumps(
            {
                "committed": apply_report["committed"],
                "explicit_deleted": apply_report["explicit_deleted"],
                "cascade_deleted": apply_report["cascade_deleted"],
                "counts_after": {
                    k: apply_report["counts_after"][k]
                    for k in (
                        "actuaciones",
                        "relevamiento",
                        "orden_trabajo",
                        "inspeccion",
                        "actuaciones_inspector",
                        "relevamiento_relevador",
                    )
                },
                "users_fk_free": apply_report["users_unlock"]["users_test_fk_free_after_2c2b"],
                "report": str(out),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
