#!/usr/bin/env python
"""
DEPLOY-PILOT.1 — Auditoría de readiness + reporte JSON.

Uso:
  cd Backend
  python scripts/deploy_pilot_1_readiness_runner.py
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

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
REPO_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = REPO_ROOT / "Frontend"
OUTPUT_PATH = BACKEND_ROOT / "scripts/output/deploy_pilot_1_readiness_clean_db_20260922.json"

PILOT_DB_NAME = "digitaliza_pilot"
ALEMBIC_HEAD = "o0p1q2r3s4t5"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=os.name == "nt",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _frontend_build_audit() -> dict[str, Any]:
    pkg = json.loads((FRONTEND_ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = pkg.get("scripts", {})
    build_cmd = scripts.get("build", "")
    tsc_errors = 0
    npm_build_ok = False
    vite_only_ok = False

    code, npm_out = _run(["npm", "run", "build"], FRONTEND_ROOT)
    npm_build_ok = code == 0
    tsc_errors = len(re.findall(r"error TS\d+", npm_out))
    tsc_ok = tsc_errors == 0 and npm_build_ok

    code, _ = _run(["npm", "exec", "vite", "build"], FRONTEND_ROOT)
    vite_only_ok = code == 0

    return {
        "package_json": str(FRONTEND_ROOT / "package.json"),
        "build_command": build_cmd,
        "tsc_command": "tsc -b",
        "vite_command": "vite build",
        "npm_run_build_passes": npm_build_ok,
        "tsc_passes": tsc_ok,
        "tsc_error_count": tsc_errors,
        "vite_build_without_tsc_passes": vite_only_ok,
        "verdict": "BLOCKER_A" if not npm_build_ok else "PASS",
        "classification": (
            "A_blocker_real_vercel_build"
            if not npm_build_ok and tsc_errors > 0
            else (
                "B_vite_only_would_pass"
                if not npm_build_ok and vite_only_ok
                else "PASS"
            )
        ),
        "note": (
            f"npm run build = tsc -b && vite build. {tsc_errors} errores TS bloquean Vercel. "
            f"vite build solo: {'PASS' if vite_only_ok else 'FAIL'}."
            if not npm_build_ok
            else "Build de producción completo OK."
        ),
        "build_output_tail": npm_out[-2000:] if npm_out else "",
        "output_directory": "dist",
        "env_vars": {
            "required_production": ["VITE_API_BASE_URL"],
            "optional": ["VITE_PERF_LOG", "VITE_GEOCODE_SEARCH_PROVIDER"],
        },
        "vercel_json": str(FRONTEND_ROOT / "vercel.json"),
    }


def _backend_start_audit() -> dict[str, Any]:
    return {
        "entrypoint_module": "run.py",
        "wsgi_app": "run:app",
        "factory": "app.create_app (no invocar factory en gunicorn)",
        "dev_server": "python run.py (debug=True, solo local)",
        "production_start": 'gunicorn "run:app" --bind 0.0.0.0:$PORT --workers 2 --timeout 120',
        "procfile": str(BACKEND_ROOT / "Procfile"),
        "railway_toml": str(BACKEND_ROOT / "railway.toml"),
        "gunicorn_in_requirements": "gunicorn==23.0.0",
        "healthcheck_path": "/health",
    }


def _production_config_audit() -> dict[str, Any]:
    return {
        "pattern": "env-driven (no ProductionConfig class)",
        "strict_environments": ["production", "prod", "staging"],
        "ENVIRONMENT_var": "ENVIRONMENT or FLASK_ENV",
        "DEBUG": "forced False in strict mode",
        "TESTING": "forced False in strict mode",
        "JWT_SECRET_KEY": "required >= 32 chars in strict",
        "database_uri_sources": ["DATABASE_URL (Railway)", "SQLALCHEMY_DATABASE_URI"],
        "CORS_ORIGINS": "required comma-separated in strict",
        "dotenv": "load_dotenv() at create_app — cloud debe usar env del host, no .env del repo",
        "skip_escape_hatch": "SKIP_STRICT_CONFIG=1 (solo emergencias CI)",
    }


def _db_guard_audit() -> dict[str, Any]:
    from app.security.production_database import (
        FORBIDDEN_PRODUCTION_DATABASE_NAMES,
        PILOT_DATABASE_NAME,
    )

    return {
        "module": "app/security/production_database.py",
        "forbidden_database_names": sorted(FORBIDDEN_PRODUCTION_DATABASE_NAMES),
        "pilot_database_name_frozen": PILOT_DATABASE_NAME,
        "enforced_in": "enforce_strict_runtime_config (staging/production)",
    }


def _migration_from_zero() -> dict[str, Any]:
    code, out = _run([sys.executable, "scripts/migration_from_zero_test.py"], BACKEND_ROOT)
    counter = None
    for line in out.splitlines():
        if line.startswith("OT_COUNTER_INITIAL:"):
            counter = line.split(":", 1)[1].strip()
        if line.startswith("ALEMBIC_CURRENT:"):
            current = line.split(":", 1)[1].strip()
        else:
            current = None
    return {
        "script": "scripts/migration_from_zero_test.py",
        "status": "PASS" if code == 0 else "FAIL",
        "alembic_head": ALEMBIC_HEAD,
        "alembic_current_reported": current,
        "ot_counter_on_test_db": counter,
        "note": (
            "Prueba local usa digitaliza_test (puede no estar vacía). "
            "En Railway: DB vacía + flask db upgrade sin stamp."
        ),
        "output_tail": out[-1500:],
    }


def _schema_validation() -> dict[str, Any]:
    load_dotenv(BACKEND_ROOT / ".env")
    test_url = (os.getenv("TEST_DATABASE_URL") or "").strip()
    if not test_url:
        return {"status": "SKIPPED", "reason": "TEST_DATABASE_URL no configurada"}
    engine = create_engine(test_url)
    with engine.connect() as conn:
        tables = sorted(inspect(engine).get_table_names())
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        mysql_version = conn.execute(text("SELECT VERSION()")).scalar()
        charset = conn.execute(
            text(
                "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = DATABASE()"
            )
        ).mappings().first()
        distrito_cols = (
            {c["name"] for c in inspect(engine).get_columns("distrito")}
            if "distrito" in tables
            else set()
        )
    return {
        "status": "PASS" if version == ALEMBIC_HEAD else "FAIL",
        "alembic_version": version,
        "table_count": len(tables),
        "core_tables_present": [
            t
            for t in (
                "users",
                "distrito",
                "orden_trabajo",
                "orden_trabajo_contador",
                "actuaciones",
                "ruta_trabajo",
                "ruta_item",
                "iniciador_ruta",
            )
            if t in tables
        ],
        "mysql_version": str(mysql_version),
        "charset": charset["DEFAULT_CHARACTER_SET_NAME"] if charset else None,
        "collation": charset["DEFAULT_COLLATION_NAME"] if charset else None,
        "distrito_has_geom": "geom" in distrito_cols,
    }


def _seeds_audit() -> dict[str, Any]:
    return {
        "canonical_catalogs": "scripts/seed_catalogos_canonicos.py",
        "run_py_seed": "python run.py seed --csv <calles.csv> [--distritos-path]",
        "distritos_geojson": "app/domains/geolocalizacion/geocode/data/distritos.geojson",
        "distritos_srid": 4326,
        "distritos_spatial_index": "migration / seed_distritos (geom POINT/POLYGON SRID 4326)",
        "inspectores": "app/domains/grid/seeds/inspectores_canonicos.py",
        "relevadores": "app/domains/relevamientos/seeds/relevadores_canonicos.py",
        "pilot_recommendation": [
            "flask db upgrade",
            "python scripts/seed_catalogos_canonicos.py",
            "python run.py seed --csv <calles_canonicas.csv>",
            "python scripts/bootstrap_pilot_admin.py (una vez)",
        ],
        "exclude_from_pilot": [
            "relevamientos_corrientes_chico demo seed",
            "sandbox legacy data",
            "full dump restore",
        ],
    }


def main() -> int:
    frontend = _frontend_build_audit()
    migration = _migration_from_zero()
    schema = _schema_validation()

    blockers: list[str] = []
    if not frontend["npm_run_build_passes"]:
        blockers.append(
            f"Frontend npm run build falla ({frontend['tsc_error_count']} errores TypeScript; "
            "tsc es parte del build real de Vercel)."
        )

    report: dict[str, Any] = {
        "ticket": "DEPLOY-PILOT.1",
        "date": "2026-09-22",
        "generated_at": _utc_now(),
        "status": "BLOCKED" if blockers else "READY",
        "frontend_build": frontend,
        "backend_start": _backend_start_audit(),
        "production_config": _production_config_audit(),
        "db_guard": _db_guard_audit(),
        "clean_db": {
            "engine": "MySQL (Railway)",
            "pilot_database_name": PILOT_DB_NAME,
            "version": schema.get("mysql_version"),
            "charset": schema.get("charset"),
            "collation": schema.get("collation"),
            "timezone": "UTC recomendado en Railway; app usa date local Argentina en reglas de negocio",
            "migration_from_zero": migration,
            "alembic_head": ALEMBIC_HEAD,
            "schema_validation": schema,
            "seeds": _seeds_audit(),
        },
        "users_bootstrap": {
            "script": "scripts/bootstrap_pilot_admin.py",
            "env_vars": ["PILOT_ADMIN_USERNAME", "PILOT_ADMIN_EMAIL", "PILOT_ADMIN_PASSWORD"],
            "password_policy": "hash pbkdf2:sha256; nunca plaintext en repo/logs",
            "ids_created": "ejecutar en Railway post-migrate; registrar id en ops, no en repo",
        },
        "ot_counter_initial": {
            "migration_seed_requested": 89862,
            "migration_seed_display": "089862",
            "effective_on_empty_db": 89862,
            "note": (
                "En DB limpia la migración o0p1q2r3s4t5 inserta next_value=89862 si display libre. "
                "Admin puede reposicionar con PATCH /rutas-trabajo/secuencia-ot (OT-AUTO.6)."
            ),
            "do_not_copy_sandbox_cursor": True,
        },
        "vercel": {
            "status": "NOT_DEPLOYED_BY_SCRIPT",
            "root_directory": "Frontend",
            "build_command": "npm run build",
            "output_directory": "dist",
            "env": {"VITE_API_BASE_URL": "https://<railway-backend>.up.railway.app/"},
            "vercel_json_spa_rewrites": True,
            "url": None,
        },
        "railway_backend": {
            "status": "NOT_DEPLOYED_BY_SCRIPT",
            "root_directory": "Backend",
            "start_command": _backend_start_audit()["production_start"],
            "healthcheck": "/health",
            "required_env": [
                "ENVIRONMENT=production",
                "JWT_SECRET_KEY",
                "DATABASE_URL or SQLALCHEMY_DATABASE_URI",
                "CORS_ORIGINS",
            ],
            "url": None,
        },
        "railway_mysql": {
            "status": "NOT_CREATED_BY_SCRIPT",
            "database_name": PILOT_DB_NAME,
            "private_networking": "recomendado Railway service ↔ MySQL",
            "public_exposure": "evitar salvo admin temporal",
        },
        "cors": {
            "implementation": "flask-cors con CORS_ORIGINS explícito",
            "wildcard_allowed": False,
            "example": "CORS_ORIGINS=https://digitaliza.vercel.app",
        },
        "jwt": {
            "library": "Flask-JWT-Extended",
            "https_required": True,
            "login": "POST /api/auth/login",
            "bearer": "Authorization: Bearer <token>",
            "refresh": "no refresh token dedicado detectado; access JWT configurable",
            "model_change_required": False,
        },
        "password_recovery": {
            "endpoints": [
                "POST /api/auth/password-reset/request",
                "POST /api/auth/password-reset/confirm",
            ],
            "smtp_required": True,
            "pilot_decision": "B — deshabilitar UX recuperación en piloto; administración manual de passwords",
            "reason": "SMTP_PASS vacío en .env.example; sin proveedor production verificado",
            "pepper_env": "PASSWORD_RESET_PEPPER",
        },
        "filesystem_audit": {
            "runtime_writes": [
                {
                    "path": "nomenclatura_pendiente_diagnosis_service.append_suggested_aliases_to_csv",
                    "classification": "PERSISTENCE_REQUIRED",
                    "pilot_impact": "bajo — solo flujo admin nomenclatura",
                }
            ],
            "in_memory_only": [
                "osm_static_map_proxy_service PNG BytesIO",
                "export Excel/PDF en frontend (browser)",
            ],
            "epicollect_photos": "no migrar a Railway; integración remota",
            "uploads_directory": None,
        },
        "logging": {
            "production": "stdout/stderr (gunicorn + Flask logger)",
            "no_local_log_files": True,
            "sensitive_data": "no loggear passwords, JWT, reset codes",
        },
        "backups": {
            "strategy": "daily mysqldump Railway MySQL",
            "retention": "7-14 días mínimo piloto",
            "restore": "documentar procedimiento antes de datos reales",
            "status": "PENDING_OPS_SETUP",
        },
        "smoke_tests": {
            "status": "PENDING_POST_DEPLOY",
            "checklist": [
                "GET /health → 200",
                "POST login ADMIN",
                "GET perfil",
                "crear usuario piloto",
                "login usuario piloto",
            ],
        },
        "empty_db_tests": {
            "status": "PENDING_POST_DEPLOY",
            "checklist": [
                "Dashboard con 0 datos sin 500/NaN",
                "listas vacías toleradas",
                "indicadores tras QA",
            ],
        },
        "workflow_smoke": {
            "status": "PENDING_POST_DEPLOY",
            "flows": [
                "relevamiento",
                "denuncia",
                "ruta publicar OT auto",
                "completar trabajo",
            ],
        },
        "estimated_cost": {
            "vercel_hobby": "USD 0 (hobby) / Pro si equipo",
            "railway_backend": "USD ~5/mes (usage-based)",
            "railway_mysql": "USD ~5-10/mes",
            "total_pilot_estimate_usd_month": "10-20",
            "avoid": ["Redis", "K8s", "S3", "LB dedicado"],
        },
        "historical_migration_deferred": True,
        "historical_migration_principle": "SANDBOX → selección → validación → transform → insert CLEAN (no full dump)",
        "sandbox_policy": "digitaliza_sandbox intacta; no es production",
        "rollback": {
            "frontend": "redeploy Vercel deployment anterior",
            "backend": "redeploy Railway release anterior",
            "database": "restore mysqldump pre-migrate",
        },
        "blockers": blockers,
        "implemented_in_repo": [
            "GET /health",
            "gunicorn + Procfile + railway.toml",
            "production DB guard (forbidden names)",
            "DATABASE_URL support",
            "JSON 404/405/500 handlers",
            "bootstrap_pilot_admin.py",
            "migration_from_zero_test.py",
            "Frontend vercel.json SPA rewrites",
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Report: {OUTPUT_PATH}")
    print(f"Status: {report['status']}")
    if blockers:
        for b in blockers:
            print(f"BLOCKER: {b}")
    return 0 if report["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
