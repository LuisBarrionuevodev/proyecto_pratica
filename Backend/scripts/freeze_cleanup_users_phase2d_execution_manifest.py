#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3L.1 — congelar execution manifest FASE 2D USERS (833 SAFE).

Uso:
  cd Backend
  python scripts/freeze_cleanup_users_phase2d_execution_manifest.py
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

from app.domains.predeploy_cleanup.users_phase2d_manifest_freeze import (
    ManifestFreezeError,
    run_users_phase2d_manifest_freeze,
    write_freeze_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
DIAG_3L = OUTPUT_DIR / "cleanup_users_phase2d_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
MANIFEST_OUT = OUTPUT_DIR / "cleanup_execution_manifest_users_phase2d_20260920.json"
FREEZE_REPORT = OUTPUT_DIR / "cleanup_users_phase2d_manifest_freeze_20260920.json"

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
]


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    for p in (DIAG_3L, PROTECTED):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        try:
            report = run_users_phase2d_manifest_freeze(
                conn,
                diag_path=DIAG_3L,
                protected_path=PROTECTED,
                manifest_paths=MANIFEST_PATHS,
            )
        except ManifestFreezeError as exc:
            raise SystemExit(f"ABORT manifest freeze: {exc}") from exc

    write_freeze_report(report, FREEZE_REPORT)
    manifest = report["manifest"]
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    m = manifest
    print("=== PREDEPLOY-CLEANUP.3L.1 FASE 2D USERS MANIFEST FREEZE ===")
    print(f"database={m['database']} alembic={m['alembic_revision']}")
    print(f"source_diag_sha256={m['source_diag_sha256']}")
    print(f"safe_users={len(m['entities']['users'])}")
    print(f"blocked_preserve={len(m['preserve']['blocked_test_user_ids'])}")
    print(f"fk_edges={m['fk_schema']['edge_count']}")
    print(f"expected_effects={m['expected_effects']}")
    print(f"users_after={m['expected_users_after']}")
    print(f"protected_intersection={m['protected_intersection']}")
    print(f"identity_snapshot_hash={m['identity_snapshot_hash']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Manifest: {MANIFEST_OUT}")
    print(f"  sha256: {report['manifest_sha256']}")
    print(f"Freeze report: {FREEZE_REPORT}")


if __name__ == "__main__":
    main()
