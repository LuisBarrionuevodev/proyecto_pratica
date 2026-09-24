#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3E.1 — congelar execution manifest FASE 2C.1 (read-only).

Uso:
  cd Backend
  python scripts/freeze_cleanup_phase2c1_execution_manifest.py
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

from app.domains.predeploy_cleanup.phase2c1_sources_manifest_freeze import (
    ManifestFreezeError,
    run_phase2c1_manifest_freeze,
    write_freeze_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
DIAG = OUTPUT_DIR / "cleanup_phase2c1_unlocked_sources_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
STRUCTURED = OUTPUT_DIR / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
MANIFEST_OUT = OUTPUT_DIR / "cleanup_execution_manifest_phase2c1_sources_20260920.json"
FREEZE_REPORT = OUTPUT_DIR / "cleanup_phase2c1_sources_manifest_freeze_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    for p in (DIAG, PROTECTED, STRUCTURED):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        try:
            report = run_phase2c1_manifest_freeze(
                conn,
                diag_path=DIAG,
                protected_path=PROTECTED,
                structured_acts_path=STRUCTURED,
            )
        except ManifestFreezeError as exc:
            raise SystemExit(f"ABORT manifest freeze: {exc}") from exc

    write_freeze_report(report, FREEZE_REPORT)
    manifest = report["manifest"]
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    m = manifest
    print("=== PREDEPLOY-CLEANUP.3E.1 FASE 2C.1 MANIFEST FREEZE ===")
    print(f"database={m['database']} alembic={m['alembic_revision']}")
    print(f"safe_set_counts={m['safe_set_counts']}")
    cascade_counts = {k: v["count"] for k, v in m["expected_cascades"].items()}
    print(f"expected_cascades counts: {cascade_counts}")
    print(f"preserve_document_refs notif={len(m['preserve_document_refs']['notificacion'])} comp={len(m['preserve_document_refs']['comprobacion'])}")
    print(f"protected_intersection={m['protected_intersection']}")
    print(f"delete_order={m['delete_order']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Manifest: {MANIFEST_OUT}")
    print(f"  sha256: {report['manifest_sha256']}")
    print(f"Freeze report: {FREEZE_REPORT}")


if __name__ == "__main__":
    main()
