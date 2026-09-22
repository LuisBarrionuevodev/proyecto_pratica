#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3K-DIAG — ADMIN-GRAPH auditoría residual administrativo test.

Uso:
  cd Backend
  python scripts/diag_cleanup_admin_graph.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.admin_graph_diag import run_admin_graph_diag, write_diag_report

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
APPLY_2C2B = OUTPUT_DIR / "cleanup_phase2c2b_sources_apply_20260920_142126.json"
PHASE2C2C_MANIFEST = OUTPUT_DIR / "cleanup_execution_manifest_phase2c2c_orphan_documents_20260920.json"
OUT = OUTPUT_DIR / "cleanup_admin_graph_diag_20260920.json"

MANIFEST_PATHS = [
    OUTPUT_DIR / "cleanup_execution_manifest_phase1_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c1_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_prime_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2c_orphan_documents_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_route_residual_20260920.json",
]


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    for p in (PROTECTED, APPLY_2C2B):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_admin_graph_diag(
            conn,
            protected_path=PROTECTED,
            apply_2c2b_path=APPLY_2C2B,
            manifest_paths=MANIFEST_PATHS,
            phase2c2c_manifest_path=PHASE2C2C_MANIFEST,
            backend_root=BACKEND_ROOT,
        )

    write_diag_report(report, OUT)

    cc = report["connected_components"]
    safe = report["safe_sets"]
    print("=== PREDEPLOY-CLEANUP.3K-DIAG ADMIN-GRAPH ===")
    print(f"baseline_ok={report['baseline']['baseline_ok']}")
    if report["baseline"]["drift"]:
        print(f"DRIFT: {report['baseline']['drift']}")
    print(f"notif_exist={report['candidate_universe']['notificaciones_blocked_25']['exist_count']}/25")
    print(f"exp_exist={report['candidate_universe']['expedientes_27']['exist_count']}/27")
    print(f"connected_components={cc['count']} (simple={cc['simple_notif_exp_count']}, comp2289={cc['comp_2289_component_count']})")
    print(f"source_119_in_25={report['test_provenance']['source_119']['actual_count']}")
    print(f"safe_simple={report['component_classification']['safe_simple_count']}/25")
    print(f"component_2289={report['component_classification']['component_2289']['status']}")
    print(f"SAFE_NOTIF={len(safe['SAFE_ADMIN_NOTIFICACION'])} SAFE_EXP={len(safe['SAFE_ADMIN_EXPEDIENTE'])}")
    print(f"protected_closure_valid={report['protected_closure']['valid']}")
    print(f"known_test_guards_ok={report['known_test_guards']['guard_ok']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
