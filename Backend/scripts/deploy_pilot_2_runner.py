#!/usr/bin/env python
"""
DEPLOY-PILOT.2 — Pre-flight local + reporte JSON (primer deploy cloud).

No crea recursos Railway/Vercel ni escribe secretos en el reporte.
Ejecuta gates locales y documenta pasos manuales pendientes.

Uso:
  cd Backend
  python scripts/deploy_pilot_2_runner.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = REPO_ROOT / "Frontend"
OUTPUT_PATH = BACKEND_ROOT / "scripts/output/deploy_pilot_2_first_cloud_deploy_20260922.json"

PILOT_DB_NAME = "digitaliza_pilot"
ALEMBIC_HEAD = "o0p1q2r3s4t5"
CALLES_CSV = (
    BACKEND_ROOT / "app/domains/catalogos/canonical/data/calles_canonicas.csv"
)
OT_PILOT_START = 4000


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=os.name == "nt",
        timeout=timeout,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _git_commit() -> str:
    code, out = _run(["git", "rev-parse", "HEAD"], REPO_ROOT)
    return out if code == 0 else "unknown"


def _git_dirty() -> dict[str, Any]:
    code, out = _run(["git", "status", "--porcelain"], REPO_ROOT)
    if code != 0:
        return {"dirty": True, "error": out}
    lines = [ln for ln in out.splitlines() if ln.strip()]
    return {
        "dirty": len(lines) > 0,
        "changed_files": len(lines),
        "sample": lines[:20],
    }


def _cli_auth() -> dict[str, Any]:
    railway_code, railway_out = _run(
        ["npx", "@railway/cli@latest", "whoami"], REPO_ROOT, timeout=60
    )
    vercel_code, vercel_out = _run(["npx", "vercel@latest", "whoami"], REPO_ROOT, timeout=60)
    return {
        "railway": {
            "authenticated": railway_code == 0 and "Unauthorized" not in railway_out,
            "detail": "ok" if railway_code == 0 else railway_out[:200],
        },
        "vercel": {
            "authenticated": vercel_code == 0 and "Logged out" not in vercel_out,
            "detail": "ok" if vercel_code == 0 else vercel_out[:200],
        },
    }


def _preflight() -> dict[str, Any]:
    npm_code, npm_out = _run(["npm", "run", "build"], FRONTEND_ROOT, timeout=180)
    health_code, health_out = _run(
        ["python", "-m", "pytest", "tests/test_deploy_pilot_health.py", "-q"],
        BACKEND_ROOT,
        timeout=120,
    )
    mig_code, mig_out = _run(
        ["python", "scripts/migration_from_zero_test.py"], BACKEND_ROOT, timeout=180
    )
    alembic_match = re.search(r"ALEMBIC_CURRENT:\s*(\S+)", mig_out)
    counter_match = re.search(r"OT_COUNTER_INITIAL:\s*(\d+)", mig_out)
    return {
        "npm_run_build": {"pass": npm_code == 0, "exit_code": npm_code},
        "deploy_pilot_health": {"pass": health_code == 0, "exit_code": health_code},
        "migration_from_zero": {
            "pass": mig_code == 0,
            "exit_code": mig_code,
            "alembic_head": alembic_match.group(1) if alembic_match else None,
            "ot_counter_migration_seed": int(counter_match.group(1)) if counter_match else None,
        },
        "all_pass": npm_code == 0 and health_code == 0 and mig_code == 0,
    }


def _manual_runbook() -> dict[str, Any]:
    return {
        "git": [
            "Commit + push todos los archivos de deploy (Procfile, railway.toml, vercel.json, TS fixes, etc.).",
            "NO commitear .env ni secretos.",
        ],
        "railway": [
            "npx @railway/cli login",
            "Crear proyecto 'Digitaliza Pilot' con servicios Backend + MySQL.",
            f"Crear DB {PILOT_DB_NAME} (MySQL 8, utf8mb4).",
            "Variables backend: ENVIRONMENT=production, DATABASE_URL, JWT_SECRET_KEY (>=32, nuevo), CORS_ORIGINS (tras Vercel).",
            "Deploy backend (root=Backend). Healthcheck GET /health.",
            "flask db upgrade (HEAD " + ALEMBIC_HEAD + ").",
            "python scripts/seed_catalogos_canonicos.py",
            f"python run.py seed --csv {CALLES_CSV.as_posix()}",
            "PILOT_ADMIN_* → python scripts/bootstrap_pilot_admin.py",
            f"PATCH /rutas-trabajo/secuencia-ot requested={OT_PILOT_START} (ADMIN, antes de publicar rutas).",
        ],
        "vercel": [
            "npx vercel login",
            "Proyecto root=Frontend, build=npm run build, output=dist.",
            "VITE_API_BASE_URL=https://<railway-backend>",
            "Actualizar CORS_ORIGINS en Railway con URL production Vercel.",
        ],
        "smoke": [
            "Login ADMIN, empty DB UI, catálogos, crear USUARIO piloto.",
            "QA: relevamiento, denuncia, actuación, ACT-HIST, ruta + publicar OT 004xxx, completar trabajo.",
            "Dashboard sin Pendientes, export Excel/PDF, backup MySQL antes de usuarios reales.",
        ],
    }


def main() -> int:
    preflight = _preflight()
    git = _git_dirty()
    cli = _cli_auth()

    blockers: list[str] = []
    if not preflight["all_pass"]:
        blockers.append("PREFLIGHT_LOCAL_FAIL")
    if git["dirty"]:
        blockers.append("GIT_UNCOMMITTED_CHANGES")
    if not cli["railway"]["authenticated"]:
        blockers.append("RAILWAY_CLI_NOT_AUTHENTICATED")
    if not cli["vercel"]["authenticated"]:
        blockers.append("VERCEL_CLI_NOT_AUTHENTICATED")

    status = "BLOCKED" if blockers else "PARTIAL"
    if not blockers and preflight["all_pass"]:
        status = "PARTIAL"  # cloud steps still manual until executed

    report: dict[str, Any] = {
        "ticket": "DEPLOY-PILOT.2",
        "title": "First Cloud Deploy — Digitaliza Pilot",
        "generated_at": _utc_now(),
        "git_commit": _git_commit(),
        "git": git,
        "preflight_local": preflight,
        "cli_auth": cli,
        "railway": {
            "backend_url": None,
            "health": None,
            "deploy_status": "not_started",
            "config_files": ["Backend/Procfile", "Backend/railway.toml"],
            "start_command": 'gunicorn "run:app" --bind 0.0.0.0:$PORT --workers 2 --timeout 120',
            "healthcheck": "GET /health → 200 {\"status\":\"ok\"}",
        },
        "mysql": {
            "database": PILOT_DB_NAME,
            "version": None,
            "alembic_head_expected": ALEMBIC_HEAD,
            "alembic_head": None,
            "catalogs": None,
            "streets": None,
            "districts": None,
            "calles_csv": str(CALLES_CSV.relative_to(REPO_ROOT)),
        },
        "admin_bootstrap": {
            "script": "scripts/bootstrap_pilot_admin.py",
            "env_vars": ["PILOT_ADMIN_USERNAME", "PILOT_ADMIN_EMAIL", "PILOT_ADMIN_PASSWORD"],
            "completed": False,
        },
        "ot_counter": {
            "migration_seed": preflight["migration_from_zero"].get("ot_counter_migration_seed"),
            "requested_pilot_start": OT_PILOT_START,
            "effective_pilot_start": None,
            "reposition_endpoint": "PATCH /rutas-trabajo/secuencia-ot",
            "reposition_motivo": "Inicialización de rango OT para piloto limpio",
            "note": "NO publicar rutas antes del reposition ADMIN.",
        },
        "vercel": {
            "frontend_url": None,
            "build_status": "local_pass" if preflight["npm_run_build"]["pass"] else "fail",
            "root": "Frontend",
            "build": "npm run build",
            "output": "dist",
            "env": {"VITE_API_BASE_URL": "<Railway backend HTTPS>"},
        },
        "cors": {"configured": False, "origins": None},
        "auth": {"admin_login": None, "jwt": None},
        "empty_db_ui": None,
        "smoke": {
            "user": "pending",
            "relevamiento": "pending",
            "denuncia": "pending",
            "act_normal": "pending",
            "act_hist": "pending",
            "route": "pending",
            "ot_publish": "pending",
            "completar": "pending",
            "dashboard": "pending",
            "exports": "pending",
        },
        "security_checks": {
            "password_recovery_disabled": True,
            "no_secrets_in_report": True,
            "production_db_guard": "digitaliza_test/sandbox forbidden",
        },
        "logs": None,
        "backup": {"status": "pending_before_real_users"},
        "sandbox_untouched": True,
        "historical_migration_deferred": True,
        "manual_runbook": _manual_runbook(),
        "blockers": blockers,
        "status": status,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_PATH), "status": status, "blockers": blockers}, indent=2))
    return 0 if preflight["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
