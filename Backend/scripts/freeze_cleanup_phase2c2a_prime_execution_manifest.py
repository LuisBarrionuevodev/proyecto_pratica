#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3H.1 — congelar execution manifest FASE 2C.2A' (12 ruta_item + 38 iniciadores).

Uso:
  cd Backend
  python scripts/freeze_cleanup_phase2c2a_prime_execution_manifest.py
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

from app.domains.predeploy_cleanup.phase2c2a_prime_wrappers_manifest_freeze import (
    ManifestFreezeError,
    run_phase2c2a_prime_manifest_freeze,
    write_freeze_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
SOURCE_DIAG = OUTPUT_DIR / "cleanup_phase2c2a_prime_residual_acts_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
APPLY_2C2B = OUTPUT_DIR / "cleanup_phase2c2b_sources_apply_20260920_142126.json"
MANIFEST_OUT = OUTPUT_DIR / "cleanup_execution_manifest_phase2c2a_prime_wrappers_20260920.json"
FREEZE_REPORT = OUTPUT_DIR / "cleanup_phase2c2a_prime_wrappers_manifest_freeze_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    for p in (SOURCE_DIAG, PROTECTED, APPLY_2C2B):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        try:
            report = run_phase2c2a_prime_manifest_freeze(
                conn,
                source_diag_path=SOURCE_DIAG,
                protected_path=PROTECTED,
                apply_2c2b_path=APPLY_2C2B,
            )
        except ManifestFreezeError as exc:
            raise SystemExit(f"ABORT manifest freeze: {exc}") from exc

    write_freeze_report(report, FREEZE_REPORT)
    manifest = report["manifest"]
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    m = manifest
    print("=== PREDEPLOY-CLEANUP.3H.1 FASE 2C.2A' MANIFEST FREEZE ===")
    print(f"database={m['database']} alembic={m['alembic_revision']}")
    print(f"safe_set_counts={m['safe_set_counts']}")
    print(f"classification={m['classification']['safe_test_initiator']}+{m['classification']['safe_wrapper_around_preserved_source']}")
    print(f"delete_order={m['delete_order']}")
    print(f"unlock={m['unlock_expected']['UNLOCKED_AFTER_2C2A_PRIME']}/{m['unlock_expected']['STILL_BLOCKED']}")
    print(f"protected_intersection={m['protected_intersection']}")
    print(f"cascade_physical={m['validation']['cascade_physical_total']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Manifest: {MANIFEST_OUT}")
    print(f"  sha256: {report['manifest_sha256']}")
    print(f"Freeze report: {FREEZE_REPORT}")


if __name__ == "__main__":
    main()
