#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3C.2 — congelar execution manifest FASE 2B (read-only).

Uso:
  cd Backend
  python scripts/freeze_cleanup_phase2b_execution_manifest.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.phase2b_routes_manifest_freeze import (
    ManifestFreezeError,
    PHASE2B_DELETE_ORDER,
    run_phase2b_manifest_freeze,
    write_freeze_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
ROUTES_DIAG = OUTPUT_DIR / "cleanup_phase2b_routes_initiators_diag_20260920.json"
RECONCILE = OUTPUT_DIR / "cleanup_phase2b_route_items_reconcile_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
STRUCTURED = OUTPUT_DIR / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
DRY_RUN_V3 = OUTPUT_DIR / "cleanup_phase1_dry_run_v3_20260920_015729.json"
MANIFEST_OUT = OUTPUT_DIR / "cleanup_execution_manifest_phase2b_routes_20260920.json"
FREEZE_REPORT = OUTPUT_DIR / "cleanup_phase2b_routes_manifest_freeze_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    for p in (ROUTES_DIAG, RECONCILE, PROTECTED, STRUCTURED, DRY_RUN_V3):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        try:
            report = run_phase2b_manifest_freeze(
                conn,
                routes_diag_path=ROUTES_DIAG,
                reconcile_path=RECONCILE,
                protected_path=PROTECTED,
                structured_acts_path=STRUCTURED,
                dry_run_v3_path=DRY_RUN_V3,
            )
        except ManifestFreezeError as exc:
            raise SystemExit(f"ABORT manifest freeze: {exc}") from exc

    write_freeze_report(report, FREEZE_REPORT)
    manifest = report["manifest"]
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    v = report["manifest"]["validation"]
    print("=== PREDEPLOY-CLEANUP.3C.2 FASE 2B MANIFEST FREEZE ===")
    print(f"database={manifest['database']} alembic={manifest['alembic_revision']}")
    print("safe_set_counts:", manifest["safe_set_counts"])
    print(f"protected_intersection={manifest['protected_intersection']}")
    print(f"delete_order={manifest['delete_order']}")
    print("unlock_expectations:", json.dumps(manifest["unlock_expectations"], indent=2))
    print(f"wrapper64: {manifest['wrapper64_metadata']}")
    print(f"cascade: {v['cascade_expectations']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Manifest: {MANIFEST_OUT}")
    print(f"  sha256: {report['manifest_sha256']}")
    print(f"Freeze report: {FREEZE_REPORT}")


if __name__ == "__main__":
    main()
