#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3A-DIAG — auditoría read-only grafo bloqueado FASE 2.

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2_blockers.py

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

from app.domains.predeploy_cleanup.phase2_blockers_diag import (
    run_phase2_blockers_diag,
    write_phase2_diag_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PROTECTED_MANIFEST = OUTPUT_DIR / "protected_operational_manifest_20260920.json"
CLEANUP_MANIFEST = OUTPUT_DIR / "cleanup_manifest_phase1_20260920.json"
DRY_RUN_V3 = OUTPUT_DIR / "cleanup_phase1_dry_run_v3_20260920_015729.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    wrapper_analysis: dict = {"iniciadores_candidato_test": [], "iniciadores_proteger": []}
    if DRY_RUN_V3.is_file():
        import json

        v3 = json.loads(DRY_RUN_V3.read_text(encoding="utf-8"))
        wrap = v3.get("iniciador_wrapper_incorporated", {})
        wrapper_analysis = {
            "iniciadores_candidato_test": wrap.get("deletable_from_wrappers_64", []),
            "iniciadores_proteger": wrap.get("protected_from_wrappers_64", []),
        }

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_phase2_blockers_diag(
            conn,
            protected_manifest_path=PROTECTED_MANIFEST,
            cleanup_manifest_path=CLEANUP_MANIFEST,
            wrapper_analysis=wrapper_analysis,
        )

    out_path = OUTPUT_DIR / "cleanup_phase2_blockers_diag_20260920.json"
    write_phase2_diag_report(report, out_path)

    print(f"DATABASE: {report['baseline']['database']}")
    print(f"Alembic: {report['baseline']['alembic_version']}")
    print(f"writes_executed: {report['writes_executed']}")
    print(f"Output: {out_path}")
    print()
    print("Baseline counts:")
    for k, v in report["baseline"]["counts"].items():
        print(f"  {k}: {v}")
    print()
    print("Establecimientos test buckets:", report["establecimientos"]["bucket_counts"])
    print("Users con FK:", report["user_blockers"]["users_with_surviving_fk"])
    print("Users unlock solo EO:", report["users_unlock_simulation"]["users_unlocked_by_establecimientos_only"])
    print("Iniciadores bloqueados:", report["initiators"]["blocked_not_deleted"])
    print("Actuaciones bloqueadas:", report["acts"]["total_blocked"])
    print("Denuncias bloqueadas:", report["denuncias"]["total_blocked"])
    print("Relevamientos bloqueados:", report["relevamientos"]["total_blocked"])


if __name__ == "__main__":
    main()
