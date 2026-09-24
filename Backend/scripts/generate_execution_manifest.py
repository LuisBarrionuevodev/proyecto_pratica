#!/usr/bin/env python
"""Genera execution manifest congelado FASE 1 desde dry-run v3 validado."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from app.domains.predeploy_cleanup.execution_manifest import build_execution_manifest
from app.domains.predeploy_cleanup.manifest_io import load_manifest

DEFAULT_DRY_RUN = BACKEND_ROOT / "scripts" / "output" / "cleanup_phase1_dry_run_v3_20260920_015729.json"
DEFAULT_PROTECTED = BACKEND_ROOT / "scripts" / "output" / "protected_operational_manifest_20260920.json"
DEFAULT_CLEANUP = BACKEND_ROOT / "scripts" / "output" / "cleanup_manifest_phase1_20260920.json"
DEFAULT_XLSX = BACKEND_ROOT / "docs" / "Listado_OT_Notificacion_Inspeccion_Comprobacion_Oficio.xlsx"
DEFAULT_OUTPUT = BACKEND_ROOT / "scripts" / "output" / "cleanup_execution_manifest_phase1_20260920.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Genera execution manifest congelado FASE 1.")
    p.add_argument("--dry-run-v3", type=Path, default=DEFAULT_DRY_RUN)
    p.add_argument("--protected-manifest", type=Path, default=DEFAULT_PROTECTED)
    p.add_argument("--cleanup-manifest", type=Path, default=DEFAULT_CLEANUP)
    p.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--database-uri", default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv(BACKEND_ROOT / ".env")
    import os

    uri = (args.database_uri or os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    dry_run = json.loads(args.dry_run_v3.read_text(encoding="utf-8"))
    protected = load_manifest(args.protected_manifest)
    cleanup = load_manifest(args.cleanup_manifest)

    engine = create_engine(uri)
    with engine.connect() as conn:
        manifest = build_execution_manifest(
            conn,
            dry_run,
            protected,
            cleanup,
            source_dry_run_path=args.dry_run_v3,
            protected_manifest_path=args.protected_manifest,
            cleanup_manifest_path=args.cleanup_manifest,
            xlsx_path=args.xlsx if args.xlsx.is_file() else None,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    print(
        json.dumps(
            {
                "output": str(args.output),
                "execution_manifest_hash": manifest["execution_manifest_hash"],
                "counts": manifest["counts"],
                "writes_executed": manifest["writes_executed"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
