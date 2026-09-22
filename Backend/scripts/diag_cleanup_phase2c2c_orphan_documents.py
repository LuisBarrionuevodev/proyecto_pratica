#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3I-DIAG — FASE 2C.2C documentos huérfanos post-3H.

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2c2c_orphan_documents.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.phase2c2c_orphan_documents_diag import (
    run_phase2c2c_orphan_documents_diag,
    write_diag_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
APPLY_2C2B = OUTPUT_DIR / "cleanup_phase2c2b_sources_apply_20260920_142126.json"
APPLY_2C2B_PRIME = OUTPUT_DIR / "cleanup_phase2c2b_prime_sources_apply_20260920_155931.json"
NOTIF_SOURCE = OUTPUT_DIR / "cleanup_phase2c2_notification_source_diag_20260920.json"
RESIDUAL_GRAPH = OUTPUT_DIR / "cleanup_phase2c2_residual_graph_diag_20260920.json"
OUT = OUTPUT_DIR / "cleanup_phase2c2c_orphan_documents_diag_20260920.json"

MANIFEST_PATHS = [
    OUTPUT_DIR / "cleanup_execution_manifest_phase1_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c1_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_prime_sources_20260920.json",
]


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    for p in (PROTECTED, APPLY_2C2B, APPLY_2C2B_PRIME):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_phase2c2c_orphan_documents_diag(
            conn,
            protected_path=PROTECTED,
            apply_2c2b_path=APPLY_2C2B,
            apply_2c2b_prime_path=APPLY_2C2B_PRIME,
            manifest_paths=MANIFEST_PATHS,
            notif_source_diag_path=NOTIF_SOURCE if NOTIF_SOURCE.is_file() else None,
            residual_graph_diag_path=RESIDUAL_GRAPH if RESIDUAL_GRAPH.is_file() else None,
        )

    write_diag_report(report, OUT)

    hist = report["historical_candidate_sets"]
    notif = report["notifications"]
    comp = report["comprobaciones"]
    print("=== PREDEPLOY-CLEANUP.3I-DIAG FASE 2C.2C ===")
    print(f"baseline_ok={report['baseline']['baseline_ok']}")
    if report["baseline"]["drift"]:
        print(f"DRIFT: {report['baseline']['drift']}")
    print(f"A cap C notif={hist['intersections']['A_cap_C_notif']}")
    print(f"B cap D comp={hist['intersections']['B_cap_D_comp']}")
    print(f"NOTIF raw={hist['notif_raw_count']} SAFE={notif['safe']['count']} BLOCKED={notif['blocked']['count']}")
    print(f"COMP raw={hist['comp_raw_count']} SAFE={comp['safe']['count']} BLOCKED={comp['blocked']['count']}")
    print(f"2289 class={comp['comprobacion_2289_audit']['classification'] if comp['comprobacion_2289_audit'] else 'N/A'}")
    print(f"source_119 cap safe={report['source_119_cross']['count']}")
    print(f"known_test_acts_remaining={report['known_test_act_guard']['known_test_act_ids_remaining_count']}")
    print(f"protected_closure_valid={report['protected_closure']['valid']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
