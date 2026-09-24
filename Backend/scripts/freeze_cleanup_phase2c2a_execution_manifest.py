#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3F.2 — congelar execution manifest FASE 2C.2A (155 iniciadores).

Uso:
  cd Backend
  python scripts/freeze_cleanup_phase2c2a_execution_manifest.py
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

from app.domains.predeploy_cleanup.phase2c2a_initiators_manifest_freeze import (
    ManifestFreezeError,
    run_phase2c2a_manifest_freeze,
    write_freeze_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
SOURCE_DIAG = OUTPUT_DIR / "cleanup_phase2c2_notification_source_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
PHASE2C1_MANIFEST = OUTPUT_DIR / "cleanup_execution_manifest_phase2c1_sources_20260920.json"
MANIFEST_OUT = OUTPUT_DIR / "cleanup_execution_manifest_phase2c2a_initiators_20260920.json"
FREEZE_REPORT = OUTPUT_DIR / "cleanup_phase2c2a_initiators_manifest_freeze_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    for p in (SOURCE_DIAG, PROTECTED, PHASE2C1_MANIFEST):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        try:
            report = run_phase2c2a_manifest_freeze(
                conn,
                source_diag_path=SOURCE_DIAG,
                protected_path=PROTECTED,
                phase2c1_manifest_path=PHASE2C1_MANIFEST,
            )
        except ManifestFreezeError as exc:
            raise SystemExit(f"ABORT manifest freeze: {exc}") from exc

    write_freeze_report(report, FREEZE_REPORT)
    manifest = report["manifest"]
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    m = manifest
    print("=== PREDEPLOY-CLEANUP.3F.2 FASE 2C.2A MANIFEST FREEZE ===")
    print(f"database={m['database']} alembic={m['alembic_revision']}")
    print(f"safe_set_counts={m['safe_set_counts']}")
    print(f"delete_order={m['delete_order']}")
    print(f"unlock acts={m['unlock_expected']['actuaciones']['unlocked']}/{m['unlock_expected']['actuaciones']['blocked']}")
    print(f"unlock relev={m['unlock_expected']['relevamientos']['unlocked']}")
    print(f"protected_intersection={m['protected_intersection']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Manifest: {MANIFEST_OUT}")
    print(f"  sha256: {report['manifest_sha256']}")
    print(f"Freeze report: {FREEZE_REPORT}")


if __name__ == "__main__":
    main()
