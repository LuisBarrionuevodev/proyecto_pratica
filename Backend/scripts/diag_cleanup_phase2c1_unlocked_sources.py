#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3E-DIAG — FASE 2C.1 actuaciones + denuncias desbloqueadas.

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2c1_unlocked_sources.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.phase2c1_unlocked_sources_diag import (
    run_phase2c1_unlocked_sources_diag,
    write_diag_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
STRUCTURED = OUTPUT_DIR / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
PHASE2B_APPLY = OUTPUT_DIR / "cleanup_phase2b_routes_apply_20260920_120954.json"
OUT = OUTPUT_DIR / "cleanup_phase2c1_unlocked_sources_diag_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_phase2c1_unlocked_sources_diag(
            conn,
            protected_path=PROTECTED,
            structured_acts_path=STRUCTURED,
            phase2b_apply_path=PHASE2B_APPLY if PHASE2B_APPLY.is_file() else None,
        )

    write_diag_report(report, OUT)

    ss = report["safe_sets"]
    print("=== PREDEPLOY-CLEANUP.3E-DIAG FASE 2C.1 ===")
    print(f"baseline_ok={report['baseline']['baseline_ok']}")
    if report["baseline"]["drift"]:
        print(f"DRIFT: {report['baseline']['drift']}")
    print(f"unlocked acts: {report['acts_265']['universe']['UNLOCKED_AFTER_2B_count']}")
    print(f"  family: {report['acts_265']['universe']['family_breakdown_unlocked']}")
    print(f"SAFE_ACTUACIONES_2C1: {len(ss['SAFE_ACTUACIONES_2C1'])}")
    print(f"BLOCKED acts: {report['acts_265']['classification']['BLOCKED_count']}")
    print(f"unlocked denuncias: {report['denuncias_75']['universe']['UNLOCKED_FOR_PHASE2C_count']}")
    print(f"SAFE_DENUNCIAS_2C1: {len(ss['SAFE_DENUNCIAS_2C1'])}")
    print(f"unique OT: {report['ot_analysis']['unique_ot_from_safe_acts']}")
    print(f"SAFE_OT: {len(ss['SAFE_OT_AFTER_ACT_2C1'])}")
    print(f"protected closure valid: {report['protected_closure']['valid']}")
    print(f"users +unlocked sim: {report['user_unlock_simulation']['users_additionally_unlocked_by_2c1_sim']}")
    print(f"post_counts: {report['post_count_simulation']}")
    print(f"delete_order: {report['delete_order_recommended']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
