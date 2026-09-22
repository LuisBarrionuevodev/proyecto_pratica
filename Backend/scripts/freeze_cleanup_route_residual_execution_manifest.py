#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3J.1 — congelar execution manifest ROUTE-RESIDUAL (12 ruta_trabajo).

Uso:
  cd Backend
  python scripts/freeze_cleanup_route_residual_execution_manifest.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.route_residual_manifest_freeze import (
    ManifestFreezeError,
    run_route_residual_manifest_freeze,
    write_freeze_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
DIAG_3J = OUTPUT_DIR / "cleanup_route_residual_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
PRIME_MANIFEST = OUTPUT_DIR / "cleanup_execution_manifest_phase2c2a_prime_wrappers_20260920.json"
MANIFEST_OUT = OUTPUT_DIR / "cleanup_execution_manifest_route_residual_20260920.json"
FREEZE_REPORT = OUTPUT_DIR / "cleanup_route_residual_manifest_freeze_20260920.json"

MANIFEST_PATHS = [
    OUTPUT_DIR / "cleanup_execution_manifest_phase1_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c1_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_prime_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2c_orphan_documents_20260920.json",
]


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    for p in (DIAG_3J, PROTECTED, PRIME_MANIFEST):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        try:
            report = run_route_residual_manifest_freeze(
                conn,
                diag_path=DIAG_3J,
                protected_path=PROTECTED,
                prime_manifest_path=PRIME_MANIFEST,
                manifest_paths=MANIFEST_PATHS,
            )
        except ManifestFreezeError as exc:
            raise SystemExit(f"ABORT manifest freeze: {exc}") from exc

    write_freeze_report(report, FREEZE_REPORT)
    manifest = report["manifest"]
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    m = manifest
    print("=== PREDEPLOY-CLEANUP.3J.1 ROUTE-RESIDUAL MANIFEST FREEZE ===")
    print(f"database={m['database']} alembic={m['alembic_revision']}")
    print(f"safe_ruta_trabajo={len(m['entities']['ruta_trabajo'])}")
    print(f"cascade_physical={m['expected_cascades']['ruta_grupo']['physical_rows']}")
    print(f"delete_order={m['delete_order']}")
    print(f"post ruta_trabajo={m['expected_counts_after']['ruta_trabajo']}")
    print(f"protected_intersection={m['protected_intersection']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Manifest: {MANIFEST_OUT}")
    print(f"  sha256: {report['manifest_sha256']}")
    print(f"Freeze report: {FREEZE_REPORT}")


if __name__ == "__main__":
    main()
