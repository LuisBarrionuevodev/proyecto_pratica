#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP FASE 1 — limpieza de contaminación QA en digitaliza_sandbox.

Default: DRY-RUN (cero writes).

Uso dry-run planner (genera nuevo v3):
  python scripts/cleanup_test_contamination.py \\
    --protected-manifest scripts/output/protected_operational_manifest_20260920.json \\
    --cleanup-manifest scripts/output/cleanup_manifest_phase1_20260920.json

Dry-run contra execution manifest congelado:
  python scripts/cleanup_test_contamination.py \\
    --execution-manifest scripts/output/cleanup_execution_manifest_phase1_20260920.json \\
    --protected-manifest scripts/output/protected_operational_manifest_20260920.json \\
    --confirm-database digitaliza_sandbox

Futuro apply (NO ejecutar sin backup):
  python scripts/cleanup_test_contamination.py --apply \\
    --confirm-database digitaliza_sandbox \\
    --backup-confirmed \\
    --execution-manifest scripts/output/cleanup_execution_manifest_phase1_20260920.json \\
    --protected-manifest scripts/output/protected_operational_manifest_20260920.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from app.domains.predeploy_cleanup.apply_service import (
    ApplyAbortError,
    apply_phase1_cleanup,
    dry_run_execution_manifest,
)
from app.domains.predeploy_cleanup.manifest_io import load_manifest, manifest_sha256
from app.domains.predeploy_cleanup.planner import plan_phase1_dry_run

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cleanup contaminación test (default dry-run).")
    p.add_argument(
        "--protected-manifest",
        type=Path,
        required=True,
        help="Manifest de protección REAL (obligatorio)",
    )
    p.add_argument(
        "--cleanup-manifest",
        type=Path,
        default=None,
        help="Manifest de IDs CONFIRMADO_TEST (solo para dry-run planner, no apply)",
    )
    p.add_argument(
        "--execution-manifest",
        type=Path,
        default=None,
        help="Execution manifest congelado (requerido para apply y dry-run frozen)",
    )
    p.add_argument("--dry-run", action="store_true", default=True, help="Simular (default)")
    p.add_argument("--apply", action="store_true", help="Aplicar DELETE (requiere guardas adicionales)")
    p.add_argument("--confirm-database", default=None, help="Nombre DB esperado")
    p.add_argument("--backup-confirmed", action="store_true", help="Confirmar backup previo")
    p.add_argument("--backup-path", type=Path, default=None, help="Ruta del backup mysqldump")
    p.add_argument("--database-uri", default=None)
    p.add_argument("--output", type=Path, default=None, help="Ruta JSON reporte")
    return p.parse_args()


def validate_apply_guards(args: argparse.Namespace, db_name: str) -> None:
    """Valida guardas obligatorias para --apply."""
    if not args.apply:
        return
    missing = []
    if not args.protected_manifest or not args.protected_manifest.is_file():
        missing.append("--protected-manifest")
    execution_manifest = getattr(args, "execution_manifest", None)
    if not execution_manifest or not Path(execution_manifest).is_file():
        missing.append("--execution-manifest")
    cleanup_manifest = getattr(args, "cleanup_manifest", None)
    if cleanup_manifest and Path(cleanup_manifest).is_file():
        raise SystemExit(
            "ABORT apply: no usar --cleanup-manifest para apply; solo --execution-manifest"
        )
    if not args.confirm_database:
        missing.append("--confirm-database")
    if not args.backup_confirmed:
        missing.append("--backup-confirmed")
    if missing:
        raise SystemExit(f"ABORT apply: faltan guardas obligatorias: {', '.join(missing)}")
    if args.confirm_database != db_name:
        raise SystemExit(
            f"ABORT apply: --confirm-database={args.confirm_database} != DB conectada={db_name}"
        )


def main() -> None:
    args = parse_args()
    dry_run = not args.apply

    load_dotenv(BACKEND_ROOT / ".env")
    uri = (args.database_uri or os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    protected_manifest = load_manifest(args.protected_manifest)
    execution_manifest = None
    if args.execution_manifest:
        execution_manifest = load_manifest(args.execution_manifest)

    engine = create_engine(uri)
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT DATABASE()")).scalar()
        validate_apply_guards(args, db_name)

        if args.apply:
            if not execution_manifest:
                raise SystemExit("ABORT apply: --execution-manifest requerido")
            backup_size = None
            if args.backup_path and args.backup_path.is_file():
                backup_size = args.backup_path.stat().st_size
            try:
                report = apply_phase1_cleanup(
                    conn,
                    execution_manifest,
                    protected_manifest,
                    confirm_database=args.confirm_database,
                    backup_path=str(args.backup_path) if args.backup_path else None,
                    backup_size=backup_size,
                )
            except ApplyAbortError as exc:
                raise SystemExit(f"ABORT apply: {exc}") from exc
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = args.output or (OUTPUT_DIR / f"cleanup_phase1_apply_{ts}.json")
            out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
            print(json.dumps({"apply": True, "output": str(out), "committed": report["committed"]}, indent=2))
            return

        if execution_manifest:
            confirm_db = args.confirm_database or execution_manifest.get("database") or db_name
            try:
                report = dry_run_execution_manifest(
                    conn,
                    execution_manifest,
                    protected_manifest,
                    confirm_database=confirm_db,
                )
            except ApplyAbortError as exc:
                raise SystemExit(f"ABORT dry-run execution manifest: {exc}") from exc
            report["execution_manifest_path"] = str(args.execution_manifest)
            report["execution_manifest_hash"] = execution_manifest.get("execution_manifest_hash")
            report["protected_manifest_path"] = str(args.protected_manifest)
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = args.output or (OUTPUT_DIR / f"cleanup_phase1_dry_run_execution_{ts}.json")
            out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
            print(json.dumps({"dry_run": True, "mode": "execution_manifest", "output": str(out)}, indent=2))
            print(json.dumps(report.get("frozen_counts", {}), indent=2))
            return

        if not args.cleanup_manifest or not args.cleanup_manifest.is_file():
            raise SystemExit("ABORT: --cleanup-manifest o --execution-manifest requerido")

        cleanup_manifest = load_manifest(args.cleanup_manifest)
        report = plan_phase1_dry_run(conn, protected_manifest, cleanup_manifest)
        report["protected_manifest_path"] = str(args.protected_manifest)
        report["cleanup_manifest_path"] = str(args.cleanup_manifest)
        report["protected_manifest_hash"] = protected_manifest.get("manifest_sha256") or manifest_sha256(
            protected_manifest
        )
        report["cleanup_manifest_hash"] = cleanup_manifest.get("manifest_sha256") or manifest_sha256(
            cleanup_manifest
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = args.output or (OUTPUT_DIR / f"cleanup_phase1_dry_run_v3_{ts}.json")
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(json.dumps({"dry_run": dry_run, "output": str(out), "writes_executed": False}, indent=2))
    print(json.dumps(report["protection_report"], indent=2))
    print(json.dumps(report.get("users_summary", {}), indent=2))
    print(json.dumps(report.get("summary_table", []), indent=2))


if __name__ == "__main__":
    main()
