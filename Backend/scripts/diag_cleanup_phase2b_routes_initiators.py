#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3C-DIAG — FASE 2B rutas/iniciadores (read-only).

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2b_routes_initiators.py

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

from app.domains.predeploy_cleanup.phase2b_routes_initiators_diag import (
    run_phase2b_routes_initiators_diag,
    write_phase2b_diag_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PROTECTED_MANIFEST = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
STRUCTURED_ACTS = OUTPUT_DIR / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
PHASE2A_APPLY = OUTPUT_DIR / "cleanup_phase2a_eo_apply_20260920_112144.json"
DRY_RUN_V3 = OUTPUT_DIR / "cleanup_phase1_dry_run_v3_20260920_015729.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_phase2b_routes_initiators_diag(
            conn,
            protected_manifest_path=PROTECTED_MANIFEST,
            structured_acts_diag_path=STRUCTURED_ACTS,
            phase2a_apply_path=PHASE2A_APPLY if PHASE2A_APPLY.is_file() else None,
            dry_run_v3_path=DRY_RUN_V3 if DRY_RUN_V3.is_file() else None,
        )

    out_path = OUTPUT_DIR / "cleanup_phase2b_routes_initiators_diag_20260920.json"
    write_phase2b_diag_report(report, out_path)

    bl = report["baseline"]
    print(f"DATABASE: {bl['database']}")
    print(f"Alembic: {bl['alembic_revision']}")
    print(f"writes_executed: {report['writes_executed']}")
    print(f"Output: {out_path}")
    print()
    print("Baseline counts:")
    for k, v in bl["counts"].items():
        print(f"  {k}: {v}")
    print()
    ti = report["test_initiators"]
    print(f"Iniciadores test: {ti['count_exact']}")
    print(f"Ruta items (test ini): {report['route_items']['total']}")
    print(f"  buckets: {report['route_items']['bucket_counts']}")
    print(f"Pool rows: {report['route_pool']['total']}")
    print(f"  buckets: {report['route_pool']['bucket_counts']}")
    print(f"Rutas con items test: {report['routes']['routes_with_test_items']}")
    print(f"  clasificación: {report['routes']['classification_counts']}")
    print(f"Iniciadores final: {report['iniciadores_final']['bucket_counts']}")
    print(f"Safe sets: {report['safe_sets']['counts']}")
    af = report["actuaciones_two_families"]
    print(f"Actuaciones 413: union={af['union_count']} disjoint={af['disjoint']}")
    print(f"  unlocked_2b_sim={af['unlocked_after_2b_sim']} still_blocked={af['still_blocked_after_2b_sim']}")
    print(f"Denuncias: unlocked={report['denuncias']['unlocked_after_2b_sim']}")
    print(f"Relevamientos: unlocked={report['relevamientos']['unlocked_after_2b_sim']}")
    uu = report["user_unlock_simulation"]
    print(f"Users FK-free after 2b sim: {uu['users_test_without_any_fk_after_2b_sim']}")
    print(f"  additional vs 2A: {uu['users_additionally_unlocked_by_2b_estimate']}")


if __name__ == "__main__":
    main()
