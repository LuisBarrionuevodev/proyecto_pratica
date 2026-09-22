#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3A.1-DIAG — desambiguar 783 EO INDETERMINADOS (solo SELECT).

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2_eo_indeterminate.py
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

from app.domains.predeploy_cleanup.phase2_eo_indeterminate_diag import (
    run_eo_indeterminate_diag,
    write_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PRIOR_DIAG = OUTPUT_DIR / "cleanup_phase2_blockers_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_eo_indeterminate_diag(conn, PRIOR_DIAG, PROTECTED)

    out = OUTPUT_DIR / "cleanup_phase2_eo_indeterminate_diag_20260920.json"
    write_report(report, out)

    c = report["classification"]
    print(f"DATABASE: {report['universe_verification']['database']}")
    print(f"783 existentes: {report['universe_verification']['still_existing']}")
    print(f"writes_executed: {report['writes_executed']}")
    print()
    print("Clasificación final 783:")
    for k in ("CONFIRMADO_TEST_SEGURO", "TEST_WRAPPER_AROUND_REAL", "REAL_OPERATIVO", "INDETERMINADO"):
        print(f"  {k}: {c[k]}")
    print(f"  sum: {c['sum_check']}")
    print()
    s = report["eo_783"]["summary"]
    print(f"0 actuaciones directas: {s['cero_actuaciones_directas']}")
    print(f"solo test directas: {s['solo_test_directas']}")
    print(f"protected directas: {s['con_protected_directas']}")
    print(f"indeterminadas directas: {s['con_indeterminadas_directas']}")
    print()
    print(f"Revalidación 77: {report['revalidation_77']['still_seguro']} seguros, "
          f"{report['revalidation_77']['degraded']} degradados")
    print(f"FASE2A_EO_ONLY: {report['safe_candidates']['count_fase2a']}")
    print(f"Users liberables: {report['user_unlock_simulation']['users_liberados_inmediatamente']}")
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
