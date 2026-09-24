#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3M.2J — backup + apply FASE 2E-J JUZGADO (DELETE id=922).
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

from app.domains.catalogos.canonical.juzgados import JUZGADOS_CANONICOS
from app.domains.predeploy_cleanup.apply_phase2e_juzgado_service import (
    BASELINE_POST_2E_R,
    CATALOG_PHYSICAL_POST_2E_R,
    EXPECTED_EXEC_HASH,
    EXPECTED_PROT_HASH,
    EXPECTED_SOURCE_DIAG_HASH,
    JUZGADO_SAFE_ID,
    apply_phase2e_juzgado_cleanup,
    preflight_phase2e_juzgado_apply,
)
from app.domains.predeploy_cleanup.apply_service import ApplyAbortError
from app.domains.predeploy_cleanup.catalogs_phase2e_manifest_freeze import (
    RELEVADOR_SAFE_ID,
    load_diag_for_freeze,
)
from app.domains.predeploy_cleanup.manifest_io import file_sha256, load_manifest, manifest_sha256

EXEC_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_execution_manifest_phase2e_juzgado_20260920.json"
DIAG_PATH = BACKEND_ROOT / "scripts" / "output" / "cleanup_catalogs_phase2e_diag_20260920.json"
PHASE2E_R_REPORT = BACKEND_ROOT / "scripts" / "output" / "cleanup_phase2e_relevador_apply_20260920_183715.json"
PROTECTED_PATH = BACKEND_ROOT / "scripts" / "output" / "protected_operational_manifest_20260920.json"
OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
BACKUP_DIR = BACKEND_ROOT.parent / "backups"

EXPECTED_ALEMBIC = "l7m8n9o0p1q2"
DB_NAME = "digitaliza_sandbox"
VERIFY_DB = "digitaliza_sandbox_backup_verify_phase2e_juzgado"
MYSQL_BIN = Path(os.getenv("MYSQL_BIN", r"C:\Program Files\MySQL\MySQL Server 8.0\bin"))
FREEZE_METHOD = "backend_development_stopped_during_backup_preflight_transaction_postconditions"

MANIFEST_PATHS = [
    OUTPUT_DIR / "cleanup_execution_manifest_phase1_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2a_eo_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2b_routes_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c1_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2a_initiators_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2a_prime_wrappers_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_prime_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2c_orphan_documents_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_route_residual_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_admin_a_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_admin_b_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_users_phase2d_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2e_relevador_20260920.json",
]

BASELINE_ALL = {**BASELINE_POST_2E_R, **CATALOG_PHYSICAL_POST_2E_R}


def parse_mysql_uri(uri: str) -> dict:
    parsed = urlparse(uri.replace("+pymysql", ""))
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": (parsed.path or "").lstrip("/"),
    }


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
        results["auth_user_id"] = admin_id

    client = app.test_client()
    for key, path in [
        ("profile_me", "/api/profile/me"),
        ("actuaciones_search", "/actuaciones/search?q=20&limit=5"),
        ("rutas_list", "/rutas-trabajo"),
        ("denuncias", "/api/denuncias?limit=5"),
        ("catalogos_rubros", "/catalogos/rubros"),
        ("juzgados_catalog", "/grid/catalogs/juzgados"),
        ("relevadores_catalog", "/grid/catalogs/relevadores"),
        ("relevamientos", "/relevamientos"),
    ]:
        r = client.get(path, headers=headers)
        entry: dict = {"status": r.status_code, "ok": r.status_code == 200}
        if key == "relevamientos" and r.status_code == 500:
            entry["flag"] = "RELEVAMIENTOS-500-PREDEPLOY"
        if key == "juzgados_catalog" and r.status_code == 200:
            data = r.get_json() or {}
            items = data.get("items") or data.get("juzgados") or []
            entry["count"] = len(items)
            entry["contains_id922"] = any(
                (i.get("id") == JUZGADO_SAFE_ID or i.get("value") == JUZGADO_SAFE_ID) for i in items
            )
            jf_codes = {c for c, _ in JUZGADOS_CANONICOS}
            entry["jf_codes_present"] = sum(
                1 for i in items if (i.get("codigo") or i.get("label") or "") in jf_codes
            )
        if key == "relevadores_catalog" and r.status_code == 200:
            data = r.get_json() or {}
            items = data.get("items") or []
            entry["count"] = len(items)
            entry["contains_id2"] = any(i.get("id") == RELEVADOR_SAFE_ID for i in items)
        results[key] = entry
    return results


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = os.getenv("SQLALCHEMY_DATABASE_URI", "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    for p in (EXEC_PATH, DIAG_PATH, PROTECTED_PATH, PHASE2E_R_REPORT):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    phase2e_r_report = json.loads(PHASE2E_R_REPORT.read_text(encoding="utf-8"))
    if phase2e_r_report.get("transaction_status") != "COMMITTED":
        raise SystemExit("ABORT: 2E-R not COMMITTED")
    if not phase2e_r_report.get("phase2e_r_executed"):
        raise SystemExit("ABORT: phase2e_r_executed false")
    if phase2e_r_report.get("phase2e_j_executed"):
        raise SystemExit("ABORT: phase2e_j already executed")

    diag_data = load_diag_for_freeze(DIAG_PATH)
    execution_manifest = load_manifest(EXEC_PATH)
    exec_hash = manifest_sha256(execution_manifest)
    prot_hash = file_sha256(PROTECTED_PATH)
    diag_hash = file_sha256(DIAG_PATH)

    if exec_hash != EXPECTED_EXEC_HASH:
        raise SystemExit(f"ABORT: exec hash {exec_hash} != {EXPECTED_EXEC_HASH}")
    if diag_hash != EXPECTED_SOURCE_DIAG_HASH:
        raise SystemExit(f"ABORT: diag hash {diag_hash}")
    if execution_manifest.get("source_diag_sha256") != EXPECTED_SOURCE_DIAG_HASH:
        raise SystemExit("ABORT: source_diag_sha256 mismatch in manifest")
    if prot_hash != EXPECTED_PROT_HASH:
        raise SystemExit(f"ABORT: protected hash {prot_hash}")

    execution_manifest["_source_path"] = str(EXEC_PATH)

    engine = create_engine(uri)
    with engine.connect() as conn:
        db = conn.execute(text("SELECT DATABASE()")).scalar()
        alembic = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        if db != DB_NAME or alembic != EXPECTED_ALEMBIC:
            raise SystemExit(f"ABORT: db={db} alembic={alembic}")
        for table, expected in BASELINE_ALL.items():
            actual = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
            if actual != expected:
                raise SystemExit(f"ABORT baseline {table}: {actual} != {expected}")
        if conn.execute(text("SELECT COUNT(*) FROM oficio WHERE id = 1662")).scalar():
            raise SystemExit("ABORT: oficio 1662 exists")

    mysql = parse_mysql_uri(uri)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"digitaliza_sandbox_pre_cleanup_phase2e_juzgado_{ts}.sql"
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
        "users": 1970,
        "relevador": 10,
        "juzgado_catalogo": 843,
        "oficio": 1447,
        "calle_catalogo": 744,
        "rubro": 1224,
    }
    verify_uri = re.sub(r"/[^/]+$", f"/{VERIFY_DB}", uri)
    with create_engine(verify_uri).connect() as vconn:
        if vconn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar() != EXPECTED_ALEMBIC:
            raise SystemExit("ABORT verify alembic")
        for table, expected in verify_counts.items():
            actual = vconn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
            if actual != expected:
                raise SystemExit(f"ABORT verify {table}: {actual} != {expected}")
        if not vconn.execute(
            text("SELECT COUNT(*) FROM juzgado_catalogo WHERE id = :id"),
            {"id": JUZGADO_SAFE_ID},
        ).scalar():
            raise SystemExit("ABORT verify id922 missing")
        if vconn.execute(text("SELECT COUNT(*) FROM oficio WHERE id = 1662")).scalar():
            raise SystemExit("ABORT verify oficio 1662 present")
        missing_jf = []
        for codigo, _ in JUZGADOS_CANONICOS:
            if not vconn.execute(
                text("SELECT COUNT(*) FROM juzgado_catalogo WHERE codigo = :c"),
                {"c": codigo},
            ).scalar():
                missing_jf.append(codigo)
        if missing_jf:
            raise SystemExit(f"ABORT verify JF missing: {missing_jf}")

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

    with engine.connect() as conn:
        try:
            preflight = preflight_phase2e_juzgado_apply(
                conn,
                execution_manifest,
                PROTECTED_PATH,
                expected_exec_hash=EXPECTED_EXEC_HASH,
                expected_source_diag_hash=EXPECTED_SOURCE_DIAG_HASH,
                expected_prot_hash=EXPECTED_PROT_HASH,
                backup_confirmed=True,
                restore_verified=True,
                manifest_paths=MANIFEST_PATHS,
                diag_data=diag_data,
                phase2e_r_report=phase2e_r_report,
            )
        except ApplyAbortError as exc:
            raise SystemExit(f"ABORT preflight: {exc}") from exc

        print("PHASE2E_J_PREFLIGHT_OK")

        try:
            apply_report = apply_phase2e_juzgado_cleanup(
                conn,
                execution_manifest,
                PROTECTED_PATH,
                confirm_database=DB_NAME,
                expected_exec_hash=EXPECTED_EXEC_HASH,
                expected_source_diag_hash=EXPECTED_SOURCE_DIAG_HASH,
                expected_prot_hash=EXPECTED_PROT_HASH,
                backup_path=str(backup_path),
                backup_hash=backup_hash,
                backup_size=backup_size,
                restore_verified=True,
                freeze_method=FREEZE_METHOD,
                manifest_paths=MANIFEST_PATHS,
                diag_data=diag_data,
                phase2e_r_report=phase2e_r_report,
            )
        except ApplyAbortError as exc:
            out = OUTPUT_DIR / f"cleanup_phase2e_juzgado_apply_{ts}.json"
            out.write_text(
                json.dumps(
                    {
                        "transaction_status": "ROLLED_BACK",
                        "committed": False,
                        "writes_executed": False,
                        "phase2e_r_still_committed": True,
                        "error": str(exc),
                        "backup": {
                            "path": str(backup_path),
                            "sha256": backup_hash,
                            "size": backup_size,
                            "exit_code": 0,
                        },
                    },
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
            raise SystemExit(f"ABORT apply: {exc}") from exc

    smoke = run_smoke_qa()

    out = OUTPUT_DIR / f"cleanup_phase2e_juzgado_apply_{ts}.json"
    apply_report["backup"] = {
        "path": str(backup_path),
        "size": backup_size,
        "sha256": backup_hash,
        "exit_code": 0,
        "timestamp": datetime.now().isoformat(),
        "restore_verified": True,
    }
    apply_report["restore_verify"] = {"verified": True, "verify_db": VERIFY_DB}
    apply_report["preflight_summary"] = {"status": "PHASE2E_J_PREFLIGHT_OK"}
    apply_report["smoke_qa"] = smoke
    apply_report["writes_freeze"] = {
        "backend_stopped": True,
        "method": FREEZE_METHOD,
        "database": DB_NAME,
    }
    apply_report["manifest_hashes"] = {
        "execution": EXPECTED_EXEC_HASH,
        "source_diag": EXPECTED_SOURCE_DIAG_HASH,
        "protected": EXPECTED_PROT_HASH,
    }
    apply_report["phase2e_c_not_executed"] = True
    apply_report["phase2e_u_not_executed"] = True
    out.write_text(json.dumps(apply_report, indent=2, default=str), encoding="utf-8")

    print(
        json.dumps(
            {
                "committed": apply_report["committed"],
                "explicit_deleted": apply_report["explicit_deleted"],
                "juzgado_after": apply_report["counts_after"]["juzgado_catalogo"],
                "phase2e_closure": apply_report["phase2e_closure"],
                "report": str(out),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
