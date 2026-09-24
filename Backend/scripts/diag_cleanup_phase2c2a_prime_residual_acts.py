#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3H-DIAG — FASE 2C.2A' forense 38 actuaciones STILL_BLOCKED.

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2c2a_prime_residual_acts.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.phase2c2a_prime_residual_acts_diag import (
    run_phase2c2a_prime_residual_acts_diag,
    write_diag_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
APPLY_2C2B = OUTPUT_DIR / "cleanup_phase2c2b_sources_apply_20260920_142126.json"
DIAG_3F1 = OUTPUT_DIR / "cleanup_phase2c2_notification_source_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
STRUCTURED = OUTPUT_DIR / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
TESTS_ROOT = BACKEND_ROOT / "tests"
OUT = OUTPUT_DIR / "cleanup_phase2c2a_prime_residual_acts_diag_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = os.getenv("SQLALCHEMY_DATABASE_URI", "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    for p in (APPLY_2C2B, DIAG_3F1, PROTECTED, STRUCTURED):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_phase2c2a_prime_residual_acts_diag(
            conn,
            apply_2c2b_path=APPLY_2C2B,
            diag_3f1_path=DIAG_3F1,
            protected_path=PROTECTED,
            structured_acts_path=STRUCTURED,
            tests_root=TESTS_ROOT,
        )

    write_diag_report(report, OUT)

    if report.get("abort_reason"):
        raise SystemExit(f"ABORT: {report['abort_reason']} drift={report['baseline']['drift']}")

    acts = report["acts_38"]
    ini = report["initiators"]
    unlock = report["acts_unlock_simulation"]
    print("=== PREDEPLOY-CLEANUP.3H-DIAG FASE 2C.2A' ===")
    print(f"baseline_ok={report['baseline']['baseline_ok']}")
    print(f"acts_38 present={acts['present']} OLD={acts['family']['SET_ACT_OLD_count']} STRUCTURED={acts['family']['SET_ACT_STRUCTURED_count']}")
    print(f"unique_blocker_iniciadores={ini['unique_blocker_count']}")
    print(f"initiator_types={ini['tipo_counts']}")
    print(f"final_classification={ini['final_classification_counts']}")
    print(f"UNLOCKED={unlock['UNLOCKED_count']} STILL_BLOCKED={unlock['STILL_BLOCKED_count']}")
    print(f"SAFE_INITIATOR_2C2A_PRIME={report['safe_initiators']['count']}")
    print(f"SAFE_RI={len(report['safe_wrappers']['SAFE_RUTA_ITEM_2C2A_PRIME'])} SAFE_RP={len(report['safe_wrappers']['SAFE_RUTA_POOL_2C2A_PRIME'])}")
    print(f"protected_closure valid={report['protected_closure']['valid']}")
    print(f"recommendation={report['operational_closure_recommendation']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
