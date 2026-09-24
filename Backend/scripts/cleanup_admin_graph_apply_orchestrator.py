#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3K.2 — backup + apply ADMIN-A + ADMIN-B secuencial.
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

from app.domains.predeploy_cleanup.apply_admin_graph_service import (
    BASELINE_PRE_ADMIN_A,
    EXPECTED_ADMIN_A_HASH,
    EXPECTED_ADMIN_B_HASH,
    EXPECTED_PROT_HASH,
    EXPECTED_SOURCE_DIAG_HASH,
    POST_ADMIN_A_COUNTS,
    POST_ADMIN_B_COUNTS,
    apply_admin_a_cleanup,
    apply_admin_b_cleanup,
    post_commit_user_analysis,
    preflight_admin_a_apply,
    preflight_admin_b_apply,
    verify_post_admin_a_baseline,
)
from app.domains.predeploy_cleanup.apply_service import ApplyAbortError
from app.domains.predeploy_cleanup.manifest_io import file_sha256, load_manifest, manifest_sha256

EXEC_A = BACKEND_ROOT / "scripts" / "output" / "cleanup_execution_manifest_admin_a_20260920.json"
EXEC_B = BACKEND_ROOT / "scripts" / "output" / "cleanup_execution_manifest_admin_b_20260920.json"
PROTECTED_PATH = BACKEND_ROOT / "scripts" / "output" / "protected_operational_manifest_20260920.json"
OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
BACKUP_DIR = BACKEND_ROOT.parent / "backups"

EXPECTED_ALEMBIC = "l7m8n9o0p1q2"
DB_NAME = "digitaliza_sandbox"
VERIFY_DB_A = "digitaliza_sandbox_backup_verify_admin_a"
VERIFY_DB_B = "digitaliza_sandbox_backup_verify_admin_b"
MYSQL_BIN = Path(os.getenv("MYSQL_BIN", r"C:\Program Files\MySQL\MySQL Server 8.0\bin"))
FREEZE_METHOD = "backend_development_stopped_during_backup_preflight_transaction_postconditions"

MANIFEST_PATHS = [
    OUTPUT_DIR / "cleanup_execution_manifest_phase1_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c1_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_prime_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2c_orphan_documents_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_route_residual_20260920.json",
]

VERIFY_A_COUNTS = {
    "expediente": 2940,
    "notificacion": 2478,
    "comprobacion": 1530,
    "oficio": 1448,
    "actuaciones": 8074,
    "users": 2803,
}

VERIFY_B_COUNTS = {
    "expediente": 2915,
    "notificacion": 2453,
    "comprobacion": 1530,
    "oficio": 1448,
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


def run_backup(
    mysql: dict,
    env: dict,
    suffix: str,
    ts: str,
) -> dict:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"digitaliza_sandbox_pre_cleanup_{suffix}_{ts}.sql"
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
    print(f"Backup: {backup_path}")
    with backup_path.open("w", encoding="utf-8", newline="\n") as f:
        proc = subprocess.run(dump_cmd, stdout=f, stderr=subprocess.PIPE, text=True, env=env)
    backup_size = backup_path.stat().st_size
    backup_hash = file_sha256(backup_path)
    if proc.returncode != 0 or backup_size == 0:
        raise SystemExit(f"ABORT mysqldump rc={proc.returncode} stderr={proc.stderr[:500]}")
    return {
        "path": str(backup_path),
        "size": backup_size,
        "sha256": backup_hash,
        "exit_code": proc.returncode,
        "timestamp": datetime.now().isoformat(),
    }


def run_restore_verify(
    mysql: dict,
    env: dict,
    backup_path: Path,
    verify_db: str,
    expected_counts: dict[str, int],
    uri: str,
) -> dict:
    admin_sql = (
        f"DROP DATABASE IF EXISTS `{verify_db}`; "
        f"CREATE DATABASE `{verify_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
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
                verify_db,
            ],
            stdin=f,
            capture_output=True,
            text=True,
            env=env,
        )
    if proc_restore.returncode != 0:
        raise SystemExit(f"ABORT restore: {proc_restore.stderr[:500]}")

    verify_uri = re.sub(r"/[^/]+$", f"/{verify_db}", uri)
    with create_engine(verify_uri).connect() as vconn:
        if vconn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar() != EXPECTED_ALEMBIC:
            raise SystemExit("ABORT verify alembic")
        for table, expected in expected_counts.items():
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
            f"DROP DATABASE IF EXISTS `{verify_db}`;",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    return {"verified": True, "verify_db": verify_db}


def run_smoke_qa() -> dict:
    from flask_jwt_extended import create_access_token

    from app.database import db
    from app.main import create_app

    app = create_app()
    results: dict = {}
    with app.app_context():
        admin_id = db.session.execute(
            text("SELECT id FROM users WHERE LOWER(username) = 'admin' LIMIT 1")
        ).scalar()
        token = create_access_token(identity=str(admin_id), additional_claims={"role": "admin"})
        headers = {"Authorization": f"Bearer {token}"}

    client = app.test_client()
    for key, path in [
        ("profile_me", "/api/profile/me"),
        ("actuaciones_search", "/actuaciones/search?q=20&limit=5"),
        ("rutas_list", "/rutas-trabajo"),
        ("denuncias", "/api/denuncias?limit=5"),
        ("catalogos_rubros", "/catalogos/rubros"),
        ("relevamientos", "/relevamientos"),
    ]:
        r = client.get(path, headers=headers)
        entry = {"status": r.status_code, "ok": r.status_code == 200}
        if key == "relevamientos" and r.status_code == 500:
            entry["flag"] = "RELEVAMIENTOS-500-PREDEPLOY"
        results[key] = entry
    return results


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = os.getenv("SQLALCHEMY_DATABASE_URI", "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary: dict = {
        "ticket": "PREDEPLOY-CLEANUP.3K.2",
        "started_at": datetime.now().isoformat(),
        "writes_freeze": {"backend_stopped": True, "method": FREEZE_METHOD, "database": DB_NAME},
        "manifest_hashes": {
            "admin_a": EXPECTED_ADMIN_A_HASH,
            "admin_b": EXPECTED_ADMIN_B_HASH,
            "source_diag": EXPECTED_SOURCE_DIAG_HASH,
            "protected": EXPECTED_PROT_HASH,
        },
        "combined_counts_before": dict(BASELINE_PRE_ADMIN_A),
    }

    for p in (EXEC_A, EXEC_B, PROTECTED_PATH):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    manifest_a = load_manifest(EXEC_A)
    manifest_b = load_manifest(EXEC_B)
    protected_manifest = load_manifest(PROTECTED_PATH)
    prot_hash = file_sha256(PROTECTED_PATH)

    if manifest_sha256(manifest_a) != EXPECTED_ADMIN_A_HASH:
        raise SystemExit("ABORT: ADMIN-A hash mismatch")
    if manifest_sha256(manifest_b) != EXPECTED_ADMIN_B_HASH:
        raise SystemExit("ABORT: ADMIN-B hash mismatch")

    manifest_a["_source_path"] = str(EXEC_A)
    manifest_b["_source_path"] = str(EXEC_B)
    if prot_hash != EXPECTED_PROT_HASH:
        raise SystemExit(f"ABORT: protected hash {prot_hash}")

    mysql = parse_mysql_uri(uri)
    env = os.environ.copy()
    if mysql["password"]:
        env["MYSQL_PWD"] = str(mysql["password"])

    engine = create_engine(uri)
    admin_a_report: dict | None = None
    admin_b_report: dict | None = None
    admin_a_committed = False
    admin_b_status = "NOT_EXECUTED"

    # ---- ADMIN-A ----
    with engine.connect() as conn:
        for table, expected in BASELINE_PRE_ADMIN_A.items():
            actual = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
            if actual != expected:
                raise SystemExit(f"ABORT pre-A baseline {table}: {actual} != {expected}")

    backup_a = run_backup(mysql, env, "admin_a", ts)
    restore_a = run_restore_verify(
        mysql, env, Path(backup_a["path"]), VERIFY_DB_A, VERIFY_A_COUNTS, uri
    )

    with engine.connect() as conn:
        try:
            preflight_a = preflight_admin_a_apply(
                conn,
                manifest_a,
                protected_manifest,
                expected_exec_hash=EXPECTED_ADMIN_A_HASH,
                expected_source_diag_hash=EXPECTED_SOURCE_DIAG_HASH,
                expected_prot_hash=EXPECTED_PROT_HASH,
                backup_confirmed=True,
                manifest_paths=MANIFEST_PATHS,
                protected_path=PROTECTED_PATH,
            )
        except ApplyAbortError as exc:
            raise SystemExit(f"ABORT ADMIN-A preflight: {exc}") from exc
        print("ADMIN_A_PREFLIGHT_OK")

        try:
            admin_a_report = apply_admin_a_cleanup(
                conn,
                manifest_a,
                protected_manifest,
                confirm_database=DB_NAME,
                expected_exec_hash=EXPECTED_ADMIN_A_HASH,
                expected_source_diag_hash=EXPECTED_SOURCE_DIAG_HASH,
                expected_prot_hash=EXPECTED_PROT_HASH,
                backup_path=backup_a["path"],
                backup_hash=backup_a["sha256"],
                backup_size=backup_a["size"],
                restore_verified=restore_a["verified"],
                freeze_method=FREEZE_METHOD,
                manifest_paths=MANIFEST_PATHS,
                protected_path=PROTECTED_PATH,
            )
            admin_a_committed = admin_a_report["committed"]
        except ApplyAbortError as exc:
            admin_a_report = {
                "phase": "ADMIN_A",
                "transaction_status": "ROLLED_BACK",
                "committed": False,
                "writes_executed": False,
                "error": str(exc),
                "backup": backup_a,
                "restore_verify": restore_a,
                "preflight": preflight_a,
            }
            out_a = OUTPUT_DIR / f"cleanup_admin_a_apply_{ts}.json"
            out_a.write_text(json.dumps(admin_a_report, indent=2, default=str), encoding="utf-8")
            summary["admin_a"] = admin_a_report
            summary["admin_b"] = {"status": "NOT_EXECUTED", "reason": "ADMIN-A failed"}
            summary["writes_executed"] = False
            (OUTPUT_DIR / f"cleanup_admin_graph_apply_summary_{ts}.json").write_text(
                json.dumps(summary, indent=2, default=str), encoding="utf-8"
            )
            raise SystemExit(f"ABORT ADMIN-A apply: {exc}") from exc

    admin_a_report["backup"] = backup_a
    admin_a_report["restore_verify"] = restore_a
    out_a = OUTPUT_DIR / f"cleanup_admin_a_apply_{ts}.json"
    out_a.write_text(json.dumps(admin_a_report, indent=2, default=str), encoding="utf-8")
    print(f"ADMIN-A {admin_a_report['transaction_status']}")

    # ---- REBASELINE POST-A ----
    with engine.connect() as conn:
        try:
            rebaseline = verify_post_admin_a_baseline(conn)
        except ApplyAbortError as exc:
            raise SystemExit(f"ABORT post-A rebaseline: {exc}") from exc
    print("POST-ADMIN-A rebaseline OK")

    # ---- ADMIN-B ----
    backup_b = run_backup(mysql, env, "admin_b", ts)
    restore_b = run_restore_verify(
        mysql, env, Path(backup_b["path"]), VERIFY_DB_B, VERIFY_B_COUNTS, uri
    )

    with engine.connect() as conn:
        try:
            preflight_b = preflight_admin_b_apply(
                conn,
                manifest_b,
                protected_manifest,
                expected_exec_hash=EXPECTED_ADMIN_B_HASH,
                expected_source_diag_hash=EXPECTED_SOURCE_DIAG_HASH,
                expected_prot_hash=EXPECTED_PROT_HASH,
                backup_confirmed=True,
                admin_a_committed=admin_a_committed,
                manifest_paths=MANIFEST_PATHS,
                protected_path=PROTECTED_PATH,
            )
        except ApplyAbortError as exc:
            raise SystemExit(f"ABORT ADMIN-B preflight: {exc}") from exc
        print("ADMIN_B_PREFLIGHT_OK")

        try:
            admin_b_report = apply_admin_b_cleanup(
                conn,
                manifest_b,
                protected_manifest,
                confirm_database=DB_NAME,
                expected_exec_hash=EXPECTED_ADMIN_B_HASH,
                expected_source_diag_hash=EXPECTED_SOURCE_DIAG_HASH,
                expected_prot_hash=EXPECTED_PROT_HASH,
                backup_path=backup_b["path"],
                backup_hash=backup_b["sha256"],
                backup_size=backup_b["size"],
                restore_verified=restore_b["verified"],
                freeze_method=FREEZE_METHOD,
                admin_a_committed=admin_a_committed,
                manifest_paths=MANIFEST_PATHS,
                protected_path=PROTECTED_PATH,
            )
            admin_b_status = admin_b_report["transaction_status"]
        except ApplyAbortError as exc:
            admin_b_report = {
                "phase": "ADMIN_B",
                "transaction_status": "ROLLED_BACK",
                "committed": False,
                "writes_executed": False,
                "error": str(exc),
                "backup": backup_b,
                "restore_verify": restore_b,
                "preflight": preflight_b,
                "precondition_admin_a": {"committed": admin_a_committed},
            }
            out_b = OUTPUT_DIR / f"cleanup_admin_b_apply_{ts}.json"
            out_b.write_text(json.dumps(admin_b_report, indent=2, default=str), encoding="utf-8")
            summary["admin_a"] = {"status": "COMMITTED", "report": str(out_a)}
            summary["admin_b"] = admin_b_report
            summary["writes_executed"] = admin_a_committed
            (OUTPUT_DIR / f"cleanup_admin_graph_apply_summary_{ts}.json").write_text(
                json.dumps(summary, indent=2, default=str), encoding="utf-8"
            )
            raise SystemExit(f"ABORT ADMIN-B apply: {exc}") from exc

    admin_b_report["backup"] = backup_b
    admin_b_report["restore_verify"] = restore_b
    out_b = OUTPUT_DIR / f"cleanup_admin_b_apply_{ts}.json"
    out_b.write_text(json.dumps(admin_b_report, indent=2, default=str), encoding="utf-8")
    print(f"ADMIN-B {admin_b_report['transaction_status']}")

    with engine.connect() as conn:
        users_unlock = post_commit_user_analysis(conn)
        known = admin_b_report.get("preflight", {}).get("known_test_guards", {})

    smoke = run_smoke_qa()

    summary.update(
        {
            "admin_a": {
                "transaction_status": "COMMITTED",
                "committed": True,
                "report": str(out_a),
                "backup": backup_a,
                "explicit_deleted": admin_a_report["explicit_deleted"],
            },
            "admin_b": {
                "transaction_status": admin_b_status,
                "committed": admin_b_report["committed"],
                "report": str(out_b),
                "backup": backup_b,
                "explicit_deleted": admin_b_report["explicit_deleted"],
                "juzgado_922_status": admin_b_report.get("juzgado_922_status"),
            },
            "combined_counts_after": {
                **BASELINE_PRE_ADMIN_A,
                **POST_ADMIN_B_COUNTS,
            },
            "rebaseline_post_a": rebaseline,
            "protected_preserved": admin_b_report.get("protected_preserved"),
            "known_test_guards": known,
            "users_fk_free": users_unlock,
            "smoke_qa": smoke,
            "phase2d_executed": False,
            "phase2e_executed": False,
            "writes_executed": admin_a_committed and admin_b_report["committed"],
            "finished_at": datetime.now().isoformat(),
        }
    )
    summary_path = OUTPUT_DIR / f"cleanup_admin_graph_apply_summary_{ts}.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print(json.dumps({
        "admin_a": admin_a_report["transaction_status"],
        "admin_b": admin_b_report["transaction_status"],
        "counts_after": admin_b_report["counts_after"],
        "juzgado_922": admin_b_report.get("juzgado_922_status"),
        "users_fk_free": users_unlock["users_test_fk_free_after_admin_graph"],
        "summary": str(summary_path),
    }, indent=2))


if __name__ == "__main__":
    main()
