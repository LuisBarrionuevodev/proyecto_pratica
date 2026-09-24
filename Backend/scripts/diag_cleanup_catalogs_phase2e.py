#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3M-DIAG — FASE 2E catálogos auditoría post-2D USERS.

Uso:
  cd Backend
  python scripts/diag_cleanup_catalogs_phase2e.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.catalogs_phase2e_diag import (
    run_catalogs_phase2e_diag,
    write_diag_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
APPLY_3L2 = OUTPUT_DIR / "cleanup_users_phase2d_apply_20260920_180921.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
OUT = OUTPUT_DIR / "cleanup_catalogs_phase2e_diag_20260920.json"
CALLES_CSV = (
    BACKEND_ROOT / "app" / "domains" / "catalogos" / "canonical" / "data" / "calles_canonicas.csv"
)

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
    OUTPUT_DIR / "cleanup_execution_manifest_users_phase2d_20260920.json",
]


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    for p in (APPLY_3L2, PROTECTED, CALLES_CSV):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_catalogs_phase2e_diag(
            conn,
            apply_report_path=APPLY_3L2,
            protected_path=PROTECTED,
            manifest_paths=MANIFEST_PATHS,
            calles_csv=CALLES_CSV,
        )

    write_diag_report(report, OUT)

    pc = report["physical_counts"]
    safe = report["safe_global"]
    rec = report["recommendation_by_catalog"]
    print("=== PREDEPLOY-CLEANUP.3M-DIAG FASE 2E CATALOGS ===")
    print(f"baseline_ok={report['baseline']['baseline_ok']}")
    if report["baseline"]["drift"]:
        print(f"DRIFT: {report['baseline']['drift']}")
    print(f"physical: relevador={pc['relevador']} juzgado={pc['juzgado_catalogo']} calle={pc['calle_catalogo']} rubro={pc['rubro']}")
    print(f"canonical_missing_zero={report['canonical_missing_zero']}")
    print(f"SAFE: R={len(safe['SAFE_RELEVADORES_2E'])} J={len(safe['SAFE_JUZGADOS_2E'])} C={len(safe['SAFE_CALLES_2E'])} U={len(safe['SAFE_RUBROS_2E'])}")
    print(f"relevador_id2={report['relevadores']['id2_analysis']}")
    print(f"juzgado_922={report['juzgados']['id922_analysis'].get('classification')}")
    print(f"recommendation={rec}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
