#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3J-DIAG — ROUTE-RESIDUAL-CLEANUP (12 rutas vacías post-prime).

Uso:
  cd Backend
  python scripts/diag_cleanup_route_residual.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.route_residual_diag import (
    ROUTE_IDS_12,
    run_route_residual_diag,
    write_diag_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PRIME_MANIFEST = OUTPUT_DIR / "cleanup_execution_manifest_phase2c2a_prime_wrappers_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
OUT = OUTPUT_DIR / "cleanup_route_residual_diag_20260920.json"

MANIFEST_PATHS = [
    OUTPUT_DIR / "cleanup_execution_manifest_phase1_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c1_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2b_prime_sources_20260920.json",
    OUTPUT_DIR / "cleanup_execution_manifest_phase2c2c_orphan_documents_20260920.json",
]


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    for p in (PRIME_MANIFEST, PROTECTED):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_route_residual_diag(
            conn,
            prime_manifest_path=PRIME_MANIFEST,
            protected_path=PROTECTED,
            manifest_paths=MANIFEST_PATHS,
        )

    write_diag_report(report, OUT)

    safe = report["safe_sets"]
    print("=== PREDEPLOY-CLEANUP.3J-DIAG ROUTE-RESIDUAL ===")
    print(f"baseline_ok={report['baseline']['baseline_ok']}")
    if report["baseline"]["drift"]:
        print(f"DRIFT: {report['baseline']['drift']}")
    print(f"routes_exist={report['routes_12']['exists_count']}/12")
    print(f"classification={report['classification_buckets']}")
    print(f"SAFE_RUTA_TRABAJO={safe['SAFE_RUTA_TRABAJO_RESIDUAL']}")
    print(f"SAFE_GRUPO={len(safe['SAFE_RUTA_GRUPO_RESIDUAL'])} SAFE_RGI={len(safe['SAFE_RUTA_GRUPO_INSPECTOR_RESIDUAL'])}")
    print(f"protected_closure_valid={report['protected_closure']['valid']}")
    print(f"users_unlock_sim={report['user_unlock_simulation']['users_additionally_unlocked']}")
    print(f"admin_graph_guard OK={report['admin_graph_guard']['blocked_notificaciones_25_present']==25}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
