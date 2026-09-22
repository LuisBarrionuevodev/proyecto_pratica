#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3K.1 — congelar execution manifests ADMIN-A + ADMIN-B.

Uso:
  cd Backend
  python scripts/freeze_cleanup_admin_graph_execution_manifest.py
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

from app.domains.predeploy_cleanup.admin_graph_manifest_freeze import (
    ManifestFreezeError,
    run_admin_graph_manifest_freeze,
    write_freeze_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
DIAG_3K = OUTPUT_DIR / "cleanup_admin_graph_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
MANIFEST_A_OUT = OUTPUT_DIR / "cleanup_execution_manifest_admin_a_20260920.json"
MANIFEST_B_OUT = OUTPUT_DIR / "cleanup_execution_manifest_admin_b_20260920.json"
FREEZE_REPORT = OUTPUT_DIR / "cleanup_admin_graph_manifest_freeze_20260920.json"

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

    for p in (DIAG_3K, PROTECTED):
        if not p.is_file():
            raise SystemExit(f"Archivo requerido no encontrado: {p}")

    engine = create_engine(uri)
    with engine.connect() as conn:
        try:
            report = run_admin_graph_manifest_freeze(
                conn,
                diag_path=DIAG_3K,
                protected_path=PROTECTED,
                manifest_paths=MANIFEST_PATHS,
            )
        except ManifestFreezeError as exc:
            raise SystemExit(f"ABORT manifest freeze: {exc}") from exc

    MANIFEST_A_OUT.write_text(
        json.dumps(report["admin_a"]["manifest"], indent=2, default=str),
        encoding="utf-8",
    )
    MANIFEST_B_OUT.write_text(
        json.dumps(report["admin_b"]["manifest"], indent=2, default=str),
        encoding="utf-8",
    )
    lean_report = {
        "ticket": report["ticket"],
        "writes_executed": report["writes_executed"],
        "baseline": report["baseline"],
        "source_diag_sha256": report["source_diag_sha256"],
        "admin_a": {
            "manifest_path": str(MANIFEST_A_OUT.resolve()),
            "sha256": report["admin_a"]["manifest_sha256"],
            "counts_before": report["admin_a"]["counts"],
            "counts_after": report["admin_a"]["counts_after"],
            "tests": "tests/test_cleanup_admin_a_manifest.py (13 tests)",
        },
        "admin_b": {
            "manifest_path": str(MANIFEST_B_OUT.resolve()),
            "sha256": report["admin_b"]["manifest_sha256"],
            "counts_before_after_admin_a": report["admin_b"]["counts_before_after_admin_a"],
            "counts_after": report["admin_b"]["counts_after"],
            "tests": "tests/test_cleanup_admin_b_manifest.py (12 tests)",
        },
        "cross_wave_disjointness": report["cross_wave_disjointness"],
        "combined_postcounts": report["combined_postcounts"],
        "protected_guard": report["protected_guard"],
        "known_test_guards": report["known_test_guards"],
        "catalog_effect": report["catalog_effect"],
        "diag_summary": report["diag_summary"],
    }
    write_freeze_report(lean_report, FREEZE_REPORT)

    bl = report["baseline"]
    print("=== PREDEPLOY-CLEANUP.3K.1 ADMIN-GRAPH MANIFEST FREEZE ===")
    print(f"database={bl['database']} alembic={bl['alembic_revision']}")
    print(f"expediente_baseline={bl['expediente_baseline']} oficio_baseline={bl['oficio_baseline']}")
    print(f"ADMIN-A: exp={len(report['admin_a']['manifest']['entities']['expediente'])} "
          f"notif={len(report['admin_a']['manifest']['entities']['notificacion'])}")
    print(f"  post exp={report['admin_a']['counts_after']['expediente']} "
          f"notif={report['admin_a']['counts_after']['notificacion']}")
    print(f"  sha256: {report['admin_a']['manifest_sha256']}")
    print(f"ADMIN-B: exp=2 oficio=1 comp=1 juzgado_922=PRESERVE")
    print(f"  post exp={report['admin_b']['counts_after']['expediente']} "
          f"oficio={report['admin_b']['counts_after']['oficio']} "
          f"comp={report['admin_b']['counts_after']['comprobacion']}")
    print(f"  sha256: {report['admin_b']['manifest_sha256']}")
    print(f"cross_wave_disjoint={report['cross_wave_disjointness']['fully_disjoint']}")
    print(f"writes_executed={report['writes_executed']}")
    print(f"Manifest A: {MANIFEST_A_OUT}")
    print(f"Manifest B: {MANIFEST_B_OUT}")
    print(f"Freeze report: {FREEZE_REPORT}")


if __name__ == "__main__":
    main()
