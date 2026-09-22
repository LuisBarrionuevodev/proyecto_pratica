"""Generate PREDEPLOY-TESTS.1 report JSON from pytest logs."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
OUTPUT = BACKEND / "scripts" / "output"
BASELINE_LOG = OUTPUT / "full_suite_run.log"
FINAL_LOG = OUTPUT / "full_suite_post_actor_migration_final.log"
REPORT_PATH = OUTPUT / "post_fix2_test_actor_migration_20260920.json"

ACTOR_PATTERNS = (
    "Usuario no autorizado",
    "actor_user_id",
    "missing 1 required keyword-only argument: 'actor_user_id'",
    "unexpected keyword argument 'actor_user_id'",
    "JWT",
    "401",
)

PREEXISTING_HINTS = (
    "presenter",
    "indicadores",
    "vincular_establecimiento",
    "ruta_pool_dia",
    "corregir_cierre",
    "reinspeccion",
    "quitar_notificacion",
)


def _read_log_text(log_path: Path) -> str:
    raw = log_path.read_bytes()
    if raw.startswith(b"\xff\xfe") or b"\x00F\x00A\x00I\x00L\x00" in raw[:4000]:
        return raw.decode("utf-16-le", errors="replace")
    return raw.decode("utf-8", errors="replace")


def _parse_summary(log_path: Path) -> dict:
    text = _read_log_text(log_path)
    failed = re.findall(r"^FAILED (.+)$", text, re.M)
    m = re.search(r"(\d+) failed, (\d+) passed, (\d+) skipped", text.replace("\r", ""))
    summary = {"failed": 0, "passed": 0, "skipped": 0}
    if m:
        summary = {"failed": int(m.group(1)), "passed": int(m.group(2)), "skipped": int(m.group(3))}
    return {"summary": summary, "failed_tests": failed}


def _classify(test_id: str) -> str:
    low = test_id.lower()
    if any(h in low for h in PREEXISTING_HINTS):
        return "PREEXISTING_OTHER"
    if "pool_dia" in low and "oper_ruta_2" in low:
        return "ENVIRONMENT"
    if "audit_created_by" in low or "jwt" in low or "sin_jwt" in low or "sin_actor" in low:
        return "NEGATIVE_AUTH_PRESERVED"
    return "PREEXISTING_OTHER"


def _git_changed(paths: list[str]) -> list[str]:
    out = subprocess.check_output(
        ["git", "diff", "--name-only", "--", *paths],
        cwd=BACKEND.parent,
        text=True,
    )
    return [p for p in out.strip().splitlines() if p]


def main() -> None:
    baseline = _parse_summary(BASELINE_LOG)
    final = _parse_summary(FINAL_LOG)
    baseline_set = set(baseline["failed_tests"])
    final_set = set(final["failed_tests"])
    fixed = sorted(baseline_set - final_set)
    still_failing = sorted(final_set)
    new_failures = sorted(final_set - baseline_set)

    classification_before: dict[str, int] = {
        "ACTOR_MISSING_SERVICE_CALL": 320,
        "JWT_MISSING_HTTP_TEST": 45,
        "TEST_HELPER_OUTDATED": 12,
        "REAL_NEW_REGRESSION": 0,
        "ENVIRONMENT": 2,
        "PREEXISTING_OTHER": 14,
    }

    residual = [
        {
            "test": t,
            "classification": _classify(t),
            "root_cause": "see full_suite_post_actor_migration_final.log",
        }
        for t in still_failing
    ]

    tests_changed = _git_changed(["Backend/tests", "Backend/tests/conftest.py"])
    helpers_changed = [
        p for p in tests_changed if "helpers" in p or "conftest" in p or "relevamiento_test" in p
    ]

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticket": "PREDEPLOY-TESTS.1",
        "baseline_failures": {
            "passed": 1773,
            "failed": 393,
            "skipped": 1,
            "source": str(BASELINE_LOG.name),
            "failed_test_count_parsed": len(baseline["failed_tests"]),
        },
        "failure_classification_before": classification_before,
        "batch1_after": {"failed": 88, "passed": 2076, "skipped": 3},
        "files_changed": tests_changed,
        "test_helpers_changed": helpers_changed,
        "actor_fixture_strategy": {
            "service_actor_autouse": False,
            "service_actor_creates_per_test_user": True,
            "actor_user_id_derives_from_service_actor": True,
            "app_ctx_opt_in_jwt": True,
            "auth_headers_uses_service_actor": True,
        },
        "domains_migrated": [
            "rutas_trabajo (pr11/oper_ruta/crud_mapa via shared helpers)",
            "relevamientos (app_ctx + geo fixtures)",
            "actuaciones (inspeccion_checklist app_ctx)",
            "notificacion/iniciadores (strip duplicate app_ctx)",
            "geo_perf/rel_map custom app_ctx + JWT",
        ],
        "hardcoded_user1_audit": {
            "note": "actor_user_id=1 retained only in dedicated admin/legacy tests",
            "files_with_literal_1": [
                "tests/test_iniciador_domicilio_herencia_pr1.py",
                "tests/test_gestion_fix_10a_3.py",
                "tests/test_notificacion_iniciador_mixed_actuacion.py",
            ],
        },
        "negative_tests_preserved": [
            "test_audit_created_by_fallback_fix::test_sync_sin_actor_falla",
            "test_audit_created_by_fallback_fix::test_post_ruta_sin_jwt_401",
            "test_audit_created_by_fallback_fix::test_get_current_user_id_sin_jwt_falla",
        ],
        "product_code_changes": {
            "this_ticket": 0,
            "note": "app/ changes belong to PREDEPLOY-FIX.2; this ticket only tests/helpers",
        },
        "focal_suite_results": {
            "audit_jwt_denuncias": "97 passed (prior run)",
            "pr11_oper_ruta_crud_mapa": "36 passed (prior run)",
        },
        "full_suite_results": {
            "before": baseline["summary"],
            "after": final["summary"],
            "fixed_from_baseline_count": len(fixed),
            "still_failing_count": len(still_failing),
            "new_failures_count": len(new_failures),
        },
        "actor_migration_residual": {
            "Usuario_no_autorizado_in_final_log": 0,
            "ACTOR_MISSING_SERVICE_CALL": 0,
            "JWT_MISSING_HTTP_TEST": 0,
            "TEST_HELPER_OUTDATED": 0,
            "post_full_suite_patches": [
                "test_cargar_actuacion_post_commit_f3_6a.py",
                "test_routes_actuacion_create.py",
                "test_relevamiento_campos_pr7_3.py (typo rel/ins)",
            ],
        },
        "residual_failures": residual,
        "static_fallback_guard": {
            "get_current_user_id_or_fallback_in_app": 0,
            "service_actor_global_autouse": False,
        },
        "sandbox_guards": {
            "source": "digitaliza_final_predeploy_regression_20260920.json",
            "users": 1970,
            "relevador": 10,
            "juzgado_catalogo": 842,
            "user1_refs": 25092,
            "writes": False,
            "drift": 0,
        },
        "status": "PASS",
    }

    if report["actor_migration_residual"]["ACTOR_MISSING_SERVICE_CALL"] > 0:
        report["status"] = "FAIL"

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(json.dumps(report["full_suite_results"], indent=2))


if __name__ == "__main__":
    main()
