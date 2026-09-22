#!/usr/bin/env python
"""
OT-AUTO.6 — Tests + reporte de reposición segura del cursor OT.

Uso:
  cd Backend
  python scripts/ot_auto_6_counter_reposition_qa.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = BACKEND_ROOT / "scripts/output/ot_auto_6_counter_reposition_20260922.json"

TEST_FILES = (
    "tests/test_ot_auto_6_counter_reposition.py",
    "tests/test_ot_auto_3_secuencia.py",
    "tests/test_ot_auto_4_collision.py",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_pytest() -> tuple[bool, str]:
    cmd = [sys.executable, "-m", "pytest", *TEST_FILES, "-q", "--tb=no"]
    proc = subprocess.run(
        cmd,
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out.strip()


def _sandbox_snapshot() -> dict:
    load_dotenv(BACKEND_ROOT / ".env")
    uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri or "sandbox" not in uri.lower():
        return {
            "available": False,
            "note": "SQLALCHEMY_DATABASE_URI no apunta a sandbox; se omite lectura live.",
        }
    engine = create_engine(uri)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT next_value FROM orden_trabajo_contador "
                "ORDER BY id ASC LIMIT 1"
            )
        ).first()
        next_value = int(row[0]) if row else None
        occupied_at_4000 = bool(
            conn.execute(
                text("SELECT 1 FROM orden_trabajo WHERE numero_acta = :d LIMIT 1"),
                {"d": "004000"},
            ).first()
        )
    return {
        "available": True,
        "current_before": next_value,
        "requested": 4000,
        "occupied_at_requested": occupied_at_4000,
        "effective": None,
        "current_after": None,
        "note": (
            "Lectura read-only. Para aplicar PATCH en sandbox usar modal ADMIN "
            "con motivo explícito (ticket §28)."
        ),
    }


def main() -> int:
    tests_ok, pytest_out = _run_pytest()
    sandbox = _sandbox_snapshot()

    report = {
        "ticket": "OT-AUTO.6",
        "date": "2026-09-22",
        "generated_at": _utc_now(),
        "old_semantics": {
            "next_value": "secuencia irreversible solo forward",
            "patch_rule": "new_value > current_value",
            "reject_backward": True,
        },
        "new_semantics": {
            "next_value": "primer entero desde donde el allocator busca OT disponible",
            "patch_rule": "new_value >= 1, normalizado al primer libre >= solicitado",
            "reject_backward": False,
            "no_reuse": "numero_acta existente (cualquier año, soft-deleted, legacy)",
        },
        "patch_behavior": {
            "endpoint": "PATCH /rutas-trabajo/secuencia-ot",
            "auth": "admin + JWT",
            "reason_required": True,
            "lock": "orden_trabajo_contador FOR UPDATE",
            "returns": [
                "old_value",
                "requested_new_value",
                "effective_new_value",
                "effective_display",
            ],
            "normalization": "_primer_asignable_desde(requested)",
        },
        "sandbox": sandbox,
        "tests": {
            "pytest_command": " ".join(TEST_FILES),
            "pytest_output_tail": pytest_out[-2000:] if pytest_out else "",
            "backward_free": tests_ok,
            "backward_occupied": tests_ok,
            "forward": tests_ok,
            "same_value": tests_ok,
            "publish_after_backward": tests_ok,
            "skip_old_qa_range": tests_ok,
            "soft_deleted": tests_ok,
            "cross_year": tests_ok,
            "concurrency": tests_ok,
        },
        "audit": {
            "table": "orden_trabajo_contador_audit",
            "fields_used": [
                "old_value",
                "new_value",
                "requested_new_value",
                "reason",
                "user_id",
                "created_at",
            ],
            "migration_required": False,
        },
        "migration_required": False,
        "frontend": {
            "component": "MapaOtSecuenciaPreview",
            "modal_title": "Reposicionar inicio de secuencia OT",
            "help_text": (
                "La próxima OT se buscará desde este número. "
                "Los números ya utilizados se omitirán automáticamente."
            ),
        },
        "status": "PASS" if tests_ok else "FAIL",
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Report: {OUTPUT_PATH}")
    print(f"Status: {report['status']}")
    return 0 if tests_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
