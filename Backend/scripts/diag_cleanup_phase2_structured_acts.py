#!/usr/bin/env python
"""
PREDEPLOY-CLEANUP.3A.2-DIAG — forense actuaciones estructuradas (solo SELECT).

Uso:
  cd Backend
  python scripts/diag_cleanup_phase2_structured_acts.py
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

from app.domains.predeploy_cleanup.phase2_structured_acts_diag import (
    run_structured_acts_forensic,
    write_report,
)

OUTPUT_DIR = BACKEND_ROOT / "scripts" / "output"
PRIOR_EO = OUTPUT_DIR / "cleanup_phase2_eo_indeterminate_diag_20260920.json"
PROTECTED = OUTPUT_DIR / "protected_operational_manifest_20260920.json"


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        raise SystemExit("SQLALCHEMY_DATABASE_URI no configurada")

    engine = create_engine(uri)
    with engine.connect() as conn:
        report = run_structured_acts_forensic(conn, PRIOR_EO, PROTECTED)

    out = OUTPUT_DIR / "cleanup_phase2_eo_structured_acts_diag_20260920.json"
    write_report(report, out)

    u = report["universe"]
    c = report["classification"]
    print(f"Universe: {u['eo_count']} EO, {u['act_count']} actuaciones ({u['existing_act_ids']} existentes)")
    print(f"writes_executed: {report['writes_executed']}")
    print()
    print("Clasificación final:")
    for k in ("CONFIRMADO_TEST", "CONFIRMADO_REAL", "INDETERMINADO"):
        print(f"  {k}: {c[k]}")
    print(f"  sum: {c['sum']}")
    print()
    print("Top familias:")
    for fam in report["families"][:8]:
        print(f"  {fam['family_id']}: {fam['count']} — {fam['classification_mix']}")
    print()
    print("EO impact:", report["eo_impact"])
    print("Users unlock:", report["user_unlock_simulation"])
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
