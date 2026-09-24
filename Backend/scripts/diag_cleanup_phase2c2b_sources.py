#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3G-DIAG — FASE 2C.2B diagnóstico 110 acts + 26 relev + 110 OT.

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2c2b_sources.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.phase2c2b_sources_diag import (
    run_phase2c2b_sources_diag,
    write_diag_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
STRUCTURED = OUTPUT_DIR / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
APPLY_2C2A = OUTPUT_DIR / "cleanup_phase2c2a_initiators_apply_20260920_133421.json"
NOTIF_DIAG = OUTPUT_DIR / "cleanup_phase2c2_notification_source_diag_20260920.json"
OUT = OUTPUT_DIR / "cleanup_phase2c2b_sources_diag_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    if not APPLY_2C2A.is_file():
        raise SystemExit(f"Apply 2C.2A no encontrado: {APPLY_2C2A}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_phase2c2b_sources_diag(
            conn,
            apply_2c2a_path=APPLY_2C2A,
            protected_path=PROTECTED,
            structured_acts_path=STRUCTURED,
            notif_source_diag_path=NOTIF_DIAG if NOTIF_DIAG.is_file() else None,
            users_fk_free_post_2c2a=812,
        )

    write_diag_report(report, OUT)

    ss = report["safe_sets"]
    fam = report["acts_110"]["act_family_breakdown"]
    cascade = report["cascade_simulation"]
    print("=== PREDEPLOY-CLEANUP.3G-DIAG FASE 2C.2B ===")
    print(f"baseline_ok={report['baseline']['baseline_ok']}")
    if report["baseline"]["drift"]:
        print(f"DRIFT: {report['baseline']['drift']}")
    print(f"acts_110 present: {report['acts_110']['present_count']}/110")
    print(f"  family OLD={fam['SET_ACT_OLD_count']} STRUCTURED={fam['SET_ACT_STRUCTURED_count']} BOTH={fam['BOTH_count']}")
    print(f"SAFE_ACTUACIONES_2C2B: {len(ss['SAFE_ACTUACIONES_2C2B'])}")
    print(f"BLOCKED acts: {report['blocked_sets']['BLOCKED_ACTUACIONES_2C2B'].__len__() if isinstance(report['blocked_sets']['BLOCKED_ACTUACIONES_2C2B'], list) else 0}")
    print(f"SAFE_RELEVAMIENTOS_2C2B: {len(ss['SAFE_RELEVAMIENTOS_2C2B'])}")
    print(f"SAFE_OT_2C2B: {len(ss['SAFE_OT_2C2B'])}")
    print(f"cascade acts: {cascade['cascade_from_actuaciones']}")
    print(f"cascade rel: {cascade['cascade_from_relevamiento']}")
    print(f"protected closure valid: {report['protected_closure']['valid']}")
    print(f"users +unlocked sim: {report['user_unlock_simulation']['users_additionally_unlocked_by_2c2b_sim']}")
    print(f"post_counts: {report['post_count_simulation']}")
    print(f"delete_order: {report['delete_order_recommended']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
