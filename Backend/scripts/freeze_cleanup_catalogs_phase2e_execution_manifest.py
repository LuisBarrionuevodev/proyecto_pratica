#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3M.1 — congelar execution manifests FASE 2E (2E-R + 2E-J).

Uso:
  cd Backend
  python scripts/freeze_cleanup_catalogs_phase2e_execution_manifest.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.domains.predeploy_cleanup.catalogs_phase2e_manifest_freeze import (
    ManifestFreezeError,
    run_catalogs_phase2e_manifest_freeze,
    write_freeze_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
DIAG_3M = OUTPUT_DIR / "cleanup_catalogs_phase2e_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
MANIFEST_R = OUTPUT_DIR / "cleanup_execution_manifest_phase2e_relevador_20260920.json"
MANIFEST_J = OUTPUT_DIR / "cleanup_execution_manifest_phase2e_juzgado_20260920.json"
FREEZE_REPORT = OUTPUT_DIR / "cleanup_catalogs_phase2e_manifest_freeze_20260920.json"
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

    for p in (DIAG_3M, PROTECTED, CALLES_CSV):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        try:
            report = run_catalogs_phase2e_manifest_freeze(
                conn,
                diag_path=DIAG_3M,
                protected_path=PROTECTED,
                manifest_paths=MANIFEST_PATHS,
                calles_csv=CALLES_CSV,
            )
        except ManifestFreezeError as exc:
            raise SystemExit(f"ABORT manifest freeze: {exc}") from exc

    manifest_r = report["manifest_2e_r"]
    manifest_j = report["manifest_2e_j"]
    MANIFEST_R.write_text(json.dumps(manifest_r, indent=2, default=str), encoding="utf-8")
    MANIFEST_J.write_text(json.dumps(manifest_j, indent=2, default=str), encoding="utf-8")

    report["2e_r"]["manifest_path"] = str(MANIFEST_R.resolve())
    report["2e_j"]["manifest_path"] = str(MANIFEST_J.resolve())
    write_freeze_report(report, FREEZE_REPORT)

    # Patch manifest paths into freeze report after write
    freeze_data = json.loads(FREEZE_REPORT.read_text(encoding="utf-8"))
    freeze_data["2e_r"]["manifest_path"] = str(MANIFEST_R.resolve())
    freeze_data["2e_j"]["manifest_path"] = str(MANIFEST_J.resolve())
    FREEZE_REPORT.write_text(json.dumps(freeze_data, indent=2, default=str), encoding="utf-8")

    print("=== PREDEPLOY-CLEANUP.3M.1 FASE 2E CATALOGS MANIFEST FREEZE ===")
    print(f"baseline_ok={report['baseline']['baseline_ok']}")
    print(f"source_diag_sha256={report['source_diag_sha256']}")
    print(f"2E-R entities={manifest_r['entities']} sha={manifest_r['manifest_sha256'][:16]}...")
    print(f"2E-J entities={manifest_j['entities']} sha={manifest_j['manifest_sha256'][:16]}...")
    print(f"2E-C status=STOP 2E-U status=STOP")
    print(f"combined_postcounts={report['combined_postcounts']['after_2e_j']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Manifest R: {MANIFEST_R}")
    print(f"Manifest J: {MANIFEST_J}")
    print(f"Freeze report: {FREEZE_REPORT}")


if __name__ == "__main__":
    main()
