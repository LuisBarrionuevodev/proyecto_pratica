#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3G.1 — congelar execution manifest FASE 2C.2B.

Uso:
  cd Backend
  python scripts/freeze_cleanup_phase2c2b_execution_manifest.py
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

from app.domains.predeploy_cleanup.phase2c2b_sources_manifest_freeze import (
    ManifestFreezeError,
    run_phase2c2b_manifest_freeze,
    write_freeze_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
SOURCES_DIAG = OUTPUT_DIR / "cleanup_phase2c2b_sources_diag_20260920.json"
CASCADE_RECONCILE = OUTPUT_DIR / "cleanup_phase2c2b_cascade_reconcile_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
APPLY_2C2A = OUTPUT_DIR / "cleanup_phase2c2a_initiators_apply_20260920_133421.json"
MANIFEST_OUT = OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_sources_20260920.json"
FREEZE_REPORT = OUTPUT_DIR / "cleanup_phase2c2b_sources_manifest_freeze_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    for p in (SOURCES_DIAG, CASCADE_RECONCILE, PROTECTED):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        try:
            report = run_phase2c2b_manifest_freeze(
                conn,
                sources_diag_path=SOURCES_DIAG,
                cascade_reconcile_path=CASCADE_RECONCILE,
                protected_path=PROTECTED,
                apply_2c2a_path=APPLY_2C2A if APPLY_2C2A.is_file() else None,
            )
        except ManifestFreezeError as exc:
            raise SystemExit(f"ABORT manifest freeze: {exc}") from exc

    write_freeze_report(report, FREEZE_REPORT)
    manifest = report["manifest"]
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    m = manifest
    print("=== PREDEPLOY-CLEANUP.3G.1 FASE 2C.2B MANIFEST FREEZE ===")
    print(f"database={m['database']} alembic={m['alembic_revision']}")
    print(f"safe_set_counts={m['safe_set_counts']}")
    print(f"family OLD={m['act_family_breakdown']['SET_ACT_OLD_count']} STRUCTURED={m['act_family_breakdown']['SET_ACT_STRUCTURED_count']}")
    print(f"cascade AI physical={m['expected_cascades']['actuaciones_inspector']['physical_rows']} after={m['expected_cascades']['actuaciones_inspector']['expected_after']}")
    print(f"cascade RR physical={m['expected_cascades']['relevamiento_relevador']['physical_rows']} after={m['expected_cascades']['relevamiento_relevador']['expected_after']}")
    print(f"delete_order={m['delete_order']}")
    print(f"protected_intersection={m['protected_intersection']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Manifest: {MANIFEST_OUT}")
    print(f"  sha256: {report['manifest_sha256']}")
    print(f"Freeze report: {FREEZE_REPORT}")


if __name__ == "__main__":
    main()
