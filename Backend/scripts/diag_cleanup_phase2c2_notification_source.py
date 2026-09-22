#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3F.1-DIAG — Forense REINSPECCION_NOTIFICACION + relevamientos 26.

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2c2_notification_source.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.phase2c2_notification_source_diag import (
    run_phase2c2_notification_source_diag,
    write_diag_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PHASE2C2_DIAG = OUTPUT_DIR / "cleanup_phase2c2_residual_graph_diag_20260920.json"
PHASE2C1_MANIFEST = OUTPUT_DIR / "cleanup_execution_manifest_phase2c1_sources_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
TESTS_ROOT = BACKEND_ROOT / "tests"
OUT = OUTPUT_DIR / "cleanup_phase2c2_notification_source_diag_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_phase2c2_notification_source_diag(
            conn,
            phase2c2_diag_path=PHASE2C2_DIAG,
            phase2c1_manifest_path=PHASE2C1_MANIFEST,
            protected_path=PROTECTED,
            tests_root=TESTS_ROOT,
        )

    write_diag_report(report, OUT)

    ini = report["initiators_167"]
    acts = report["acts_unlock_simulation"]
    rel = report["relevamientos_unlock_simulation"]
    print("=== PREDEPLOY-CLEANUP.3F.1-DIAG ===")
    print(f"baseline_ok={report['baseline']['baseline_ok']}")
    print(f"initiators 167 present={ini['present']}")
    print(f"final_classification={ini['final_classification']}")
    print(f"notif_classification={report['notification_classification']}")
    print(f"from_265_preserved={report['notifications_199_frozen']['from_265_deleted_acts_count']}")
    print(f"SAFE_INITIATOR_2C2A={report['safe_initiators']['count']}")
    print(f"acts UNLOCKED={acts['UNLOCKED_AFTER_2C2A_count']} STILL_BLOCKED={acts['STILL_BLOCKED_count']}")
    print(f"rel UNLOCKED={rel['UNLOCKED_count']} STILL_BLOCKED={rel['STILL_BLOCKED_count']}")
    print(f"protected_closure_2C2A valid={report['proposed_waves']['2C.2A']['protected_closure_valid']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
