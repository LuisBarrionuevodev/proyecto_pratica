#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3F-DIAG — FASE 2C.2 grafo residual post-2C.1.

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2c2_residual_graph.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.phase2c2_residual_graph_diag import (
    run_phase2c2_residual_graph_diag,
    write_diag_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
PHASE2C1_MANIFEST = OUTPUT_DIR / "cleanup_execution_manifest_phase2c1_sources_20260920.json"
PHASE2C1_APPLY = OUTPUT_DIR / "cleanup_phase2c1_sources_apply_20260920_123853.json"
STRUCTURED = OUTPUT_DIR / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
STRUCTURED_LIST = OUTPUT_DIR / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
OUT = OUTPUT_DIR / "cleanup_phase2c2_residual_graph_diag_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_phase2c2_residual_graph_diag(
            conn,
            protected_path=PROTECTED,
            phase2c1_manifest_path=PHASE2C1_MANIFEST,
            structured_acts_path=STRUCTURED,
            structured_diag_path=STRUCTURED_LIST,
            phase2c1_apply_path=PHASE2C1_APPLY if PHASE2C1_APPLY.is_file() else None,
        )

    write_diag_report(report, OUT)

    print("=== PREDEPLOY-CLEANUP.3F-DIAG FASE 2C.2 ===")
    print(f"baseline_ok={report['baseline']['baseline_ok']}")
    if report["baseline"]["drift"]:
        print(f"DRIFT: {report['baseline']['drift']}")
    cr = report["protected_comprobacion_reconcile"]
    print(f"comprobacion reconcile: {cr['verdict']} ({cr['manifest_explicit_count']} -> {cr['manifest_closure_count']})")
    acts = report["acts_148"]
    print(f"acts_148: {acts['present_count']}/148 family={acts['family_split']['SET_ACT_OLD']} OLD + {acts['family_split']['SET_ACT_STRUCTURED']} STRUCTURED")
    print(f"blockers: {acts['blocker_summary']}")
    ini = report["initiators"]
    print(f"iniciadores relacionados: {ini['unique_iniciadores']} buckets={ini['classification_buckets']}")
    rel = report["relevamientos_26"]
    print(f"relevamientos: {rel['present_count']}/26 buckets={rel['classification_buckets']}")
    notif = report["notifications_199"]
    print(f"notificaciones 199 buckets={notif['classification_buckets']}")
    comp = report["comprobaciones_20"]
    print(f"comprobaciones 20 buckets={comp['classification_buckets']}")
    print(f"OT exclusive test: {report['ot_analysis']['deletable_after_148_acts_sim']}")
    print(f"users FK-free baseline: {report['user_unlock_simulation']['baseline_post_2c1']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
