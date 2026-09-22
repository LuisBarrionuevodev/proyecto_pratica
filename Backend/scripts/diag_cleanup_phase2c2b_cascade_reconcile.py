#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3G.0.1-DIAG — reconciliar cascades físicos FASE 2C.2B.

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2c2b_cascade_reconcile.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.phase2c2b_cascade_reconcile import (
    run_phase2c2b_cascade_reconcile,
    write_reconcile_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
SOURCES_DIAG = OUTPUT_DIR / "cleanup_phase2c2b_sources_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
OUT = OUTPUT_DIR / "cleanup_phase2c2b_cascade_reconcile_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")
    if not SOURCES_DIAG.is_file():
        raise SystemExit(f"Diag 3G no encontrado: {SOURCES_DIAG}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_phase2c2b_cascade_reconcile(
            conn,
            sources_diag_path=SOURCES_DIAG,
            protected_path=PROTECTED,
        )

    write_reconcile_report(report, OUT)

    ai = report["actuaciones_inspector_rows"]
    rr = report["relevamiento_relevador_rows"]
    print("=== PREDEPLOY-CLEANUP.3G.0.1 CASCADE RECONCILE ===")
    print(f"baseline_ok={report['baseline']['baseline_ok']}")
    print(f"actuaciones_inspector physical={ai['physical_rows']} distinct_acts={ai['distinct_actuaciones_id']}")
    print(f"  verdict: {ai['resolution_9_vs_18']['verdict']}")
    print(f"  expected_after={ai['expected_after']}")
    print(f"inspeccion physical={report['inspection_rows']['physical_rows']}")
    print(f"acta_inspeccion_item physical={report['acta_inspeccion_item_rows']['physical_rows']}")
    print(f"relevamiento_relevador physical={rr['physical_rows']} distinct_rel={rr['distinct_relevamiento_id']}")
    print(f"protected intersection={report['protected_intersection']['intersection_total']}")
    print(f"safe_sets={report['safe_sets_unchanged']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
