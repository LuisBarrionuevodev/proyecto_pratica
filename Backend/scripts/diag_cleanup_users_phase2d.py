#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3L-DIAG — FASE 2D USERS auditoría post-cleanup.

Uso:
  cd Backend
  python scripts/diag_cleanup_users_phase2d.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.users_phase2d_diag import (
    run_users_phase2d_diag,
    write_diag_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
OUT = OUTPUT_DIR / "cleanup_users_phase2d_diag_20260920.json"

MANIFEST_PATHS = [
    OUTPUT_DIR / "cleanup_execution_manifest_phase1_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2a_eo_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2b_routes_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c1_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2a_initiators_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2a_prime_wrappers_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_prime_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2c_orphan_documents_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_route_residual_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_admin_a_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_admin_b_20260920.json",
]


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    if not PROTECTED.is_file():
        raise SystemExit(f"Archivo requerido no encontrado: {PROTECTED}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_users_phase2d_diag(
            conn,
            protected_path=PROTECTED,
            manifest_paths=MANIFEST_PATHS,
            backend_root=BACKEND_ROOT,
        )

    write_diag_report(report, OUT)

    bl = report["baseline"]
    cs = report["classification_summary"]
    rec = report["recommendation"]
    print("=== PREDEPLOY-CLEANUP.3L-DIAG FASE 2D USERS ===")
    print(f"baseline_ok={bl['baseline_ok']}")
    if bl["drift"]:
        print(f"DRIFT: {bl['drift']}")
    print(f"users_total={report['users_total']}")
    print(f"fk_free={report['fk_free_users']['count']} (orientative={report['fk_free_users']['orientative_expected']})")
    print(f"fk_blocked={report['fk_blocked_users']['count']}")
    print(f"classification={cs}")
    print(f"SAFE_USERS_2D={report['safe_users']['count']}")
    print(f"BLOCKED_TEST={report['blocked_test_users']['count']}")
    print(f"INDETERMINATE={report['indeterminate_users']['count_fk_free']}+{report['indeterminate_users']['count_blocked']}")
    print(f"whitelist_real={len(report['real_user_whitelist'])}")
    print(f"protected_closure_valid={report['protected_closure']['valid']}")
    print(f"restrict_rows_sim={report['cascade_simulation']['delete_fk_graph']['restrict_rows']}")
    print(f"recommendation={rec['choice']} ({rec['label']})")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
