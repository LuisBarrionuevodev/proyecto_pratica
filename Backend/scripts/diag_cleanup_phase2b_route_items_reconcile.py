#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3C.1-DIAG — reconciliar 708 ruta_item INDETERMINADO.

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2b_route_items_reconcile.py

Solo SELECT. Sin DELETE/UPDATE/INSERT.
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

from app.domains.predeploy_cleanup.phase2b_route_items_reconcile import (
    run_phase2b_route_items_reconcile,
    write_reconcile_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PHASE2B_DIAG = OUTPUT_DIR / "cleanup_phase2b_routes_initiators_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
STRUCTURED = OUTPUT_DIR / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
DRY_RUN_V3 = OUTPUT_DIR / "cleanup_phase1_dry_run_v3_20260920_015729.json"
PHASE2A_APPLY = OUTPUT_DIR / "cleanup_phase2a_eo_apply_20260920_112144.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_phase2b_route_items_reconcile(
            conn,
            phase2b_diag_path=PHASE2B_DIAG,
            protected_manifest_path=PROTECTED,
            structured_acts_path=STRUCTURED,
            dry_run_v3_path=DRY_RUN_V3,
            phase2a_apply_path=PHASE2A_APPLY if PHASE2A_APPLY.is_file() else None,
        )

    out = OUTPUT_DIR / "cleanup_phase2b_route_items_reconcile_20260920.json"
    write_reconcile_report(report, out)

    cls = report["classification"]
    print(f"DATABASE: {report['baseline']['database']}")
    print(f"writes_executed: {report['writes_executed']}")
    print(f"Output: {out}")
    print()
    print("708 classification:")
    print(f"  CONFIRMADO_TEST_WRAPPER_SAFE: {cls['CONFIRMADO_TEST_WRAPPER_SAFE']}")
    print(f"  TEST_WRAPPER_AROUND_REAL: {cls['TEST_WRAPPER_AROUND_REAL']}")
    print(f"  REAL: {cls['REAL']}")
    print(f"  INDETERMINADO: {cls['INDETERMINADO']}")
    print(f"  sum: {cls['sum']}")
    print()
    w64 = report["wrapper64_reconcile"]
    print(f"Wrapper 64: records={w64['wrapper_records']} deletable={w64['deletable_count']} "
          f"protected={w64['protected_count']} missing_ini={w64['missing_iniciador_ids']}")
    ss = report["safe_sets"]["counts"]
    print(f"SAFE_RUTA_ITEM_FINAL: {ss['SAFE_RUTA_ITEM_FINAL']} (+{report['safe_sets']['new_from_708_reconcile']} from 708)")
    print(f"SAFE_INICIADOR_FINAL: {ss['SAFE_INICIADOR_FINAL']}")
    print(f"Acts 413 unlocked: {report['unlock_acts']['UNLOCKED_AFTER_2B']}")
    print(f"Denuncias unlocked: {report['unlock_denuncias']['UNLOCKED_AFTER_2B']}")
    print(f"Relevamientos unlocked: {report['unlock_relevamientos']['UNLOCKED_AFTER_2B']}")
    print(f"Users FK-free: {report['unlock_users']['users_test_fk_free_after_2b']}")
    print(f"Execution valid: {report['execution_validation']['valid']}")


if __name__ == "__main__":
    main()
