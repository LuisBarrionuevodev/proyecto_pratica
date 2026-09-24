#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3A.3 — reconciliar universo EO seguro FASE 2A (solo diagnóstico).

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2a_eo_reconcile.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.phase2a_eo_reconcile import (
    run_phase2a_reconcile,
    write_json,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
BLOCKERS = OUTPUT_DIR / "cleanup_phase2_blockers_diag_20260920.json"
INDET = OUTPUT_DIR / "cleanup_phase2_eo_indeterminate_diag_20260920.json"
STRUCTURED = OUTPUT_DIR / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
MANIFEST_OUT = OUTPUT_DIR / "cleanup_execution_manifest_phase2a_eo_20260920.json"
RECONCILE_OUT = OUTPUT_DIR / "cleanup_phase2a_eo_reconcile_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_phase2a_reconcile(conn, BLOCKERS, INDET, STRUCTURED, PROTECTED)

    write_json(report, RECONCILE_OUT)
    if report.get("manifest_proposal"):
        write_json(report["manifest_proposal"], MANIFEST_OUT)

    s = report["sets"]
    print(f"SET_A={len(s['SET_A'])} SET_B={len(s['SET_B'])} SET_C={len(s['SET_C'])}")
    print(f"Intersections: {s['intersection_counts']}")
    print(f"SAFE_EO_FINAL={s['SAFE_EO_FINAL_count']} (disjoint={s['arithmetic_check']['disjoint']})")
    print(f"Revalidation: valid={report['revalidation']['valid_count']} "
          f"degraded={report['revalidation']['degraded_count']} "
          f"missing={len(report['revalidation']['missing_ids'])}")
    print(f"SET NULL: {report['revalidation']['set_null_by_classification']}")
    print(f"Protected OK: {report['protected_closure']['valid']}")
    print(f"Users unlocked: {report['user_unlock_simulation']['users_unlocked_by_eo_only']}")
    print(f"writes_executed: {report['writes_executed']}")
    if report.get("manifest_proposal"):
        print(f"Manifest proposal: {MANIFEST_OUT}")
        print(f"  sha256: {report['manifest_proposal']['manifest_sha256']}")
    else:
        print(f"Manifest NOT generated: {report.get('manifest_proposal_error')}")
    print(f"Reconcile report: {RECONCILE_OUT}")


if __name__ == "__main__":
    main()
