#!/usr/bin/env python
"""Genera reporte DEPLOY-PILOT.1B desde log tsc post-fix."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
LOG = BACKEND_ROOT / "scripts/output/deploy_pilot_1b_tsc_after.log"
OUT = BACKEND_ROOT / "scripts/output/deploy_pilot_1b_typescript_phase1_20260922.json"

BEFORE = 292
LINE_RE = re.compile(r"^src/[^:]+.*error (TS\d+):")


def main() -> int:
    text = LOG.read_text(encoding="utf-8", errors="replace")
    codes = Counter()
    files = Counter()
    for line in text.splitlines():
        m = LINE_RE.search(line.strip())
        if not m:
            continue
        codes[m.group(1)] += 1
        f = line.split("(", 1)[0].strip()
        files[f] += 1

    total = sum(codes.values())
    report = {
        "ticket": "DEPLOY-PILOT.1B",
        "date": "2026-09-22",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if total < 200 and total < BEFORE else "FAIL",
        "before_error_count": BEFORE,
        "tsconfig": {
            "tests_excluded": True,
            "exclude_patterns": [
                "**/*.test.ts",
                "**/*.test.tsx",
                "**/*.spec.ts",
                "**/*.spec.tsx",
            ],
            "vitest_still_discovers_tests": True,
            "note": "tsconfig.app = productivo; vitest include=src/**/*.test.* independiente",
        },
        "fixes": {
            "casing": {
                "canonical": "src/types/local.d.ts",
                "imports_updated": [
                    "src/api/localesApi.ts",
                    "src/data/locales-test.ts",
                    "src/utils/filtersMap.ts",
                ],
            },
            "api_types": {
                "crudFormErrors": "applyCrudFormErrorsToState sin setFieldErrors en options",
                "dashboard_charts": "legend hidden → sx display none",
                "glide_grid_demo": "removed stale allowAdd on ImageCell",
            },
            "esquina": {
                "files": [
                    "src/api/actuacionesPendientesApi.ts",
                    "src/api/relevamientosPendientesApi.ts",
                ],
                "fix": "removed duplicate esquina_catalogo_id field",
            },
            "dashboard_export": {
                "file": "src/utils/exportExcelDashboard.ts",
                "fix": "removed Pendientes por distrito sheet (PERF-DASH.2)",
                "tests_updated": "src/utils/exportExcelDashboard.test.ts",
            },
            "imports_exports": {
                "operativaComprobacionBaseCache": "OperativaComprobacionTabKey from operativaComprobacionTabChange",
                "cargarActuaciones_config": "removed stale DROPDOWN_ENUMS/COMPROBACION_MOTIVOS exports",
            },
            "app_dialog": {
                "mergeSx_helper": "src/utils/muiSx.ts",
                "files": [
                    "src/ui/AppDialog.tsx",
                    "src/ui/ConfirmDialog.tsx",
                    "src/ui/ExportDataDialog.tsx",
                ],
                "fix": "mergeSx for slotProps; removed disableBackdropClick (MUI v7)",
            },
        },
        "after": {
            "total_errors": total,
            "errors_removed": BEFORE - total,
            "errors_by_code": dict(codes.most_common()),
            "errors_by_file_top20": dict(files.most_common(20)),
            "root_causes_remaining": {
                "B_PROPS_STALE": "CrudDialog, MUI sx overloads",
                "F_NULLABILITY": "GlobalFeedbackProvider, validations",
                "I_ROUTE_WORKFLOW_REFACTOR": "ActasComprobacion MRT casts, completar trabajo",
                "J_STRICTNESS": "TS6133 unused imports (~43)",
                "G_ENUM_DRIFT": "auth/roles.ts",
                "A_API_TYPES_STALE": "inspeccionChecklist, comprobacionesExportMappers",
                "L_OTHER": "misc",
            },
        },
        "vite_build": "PASS",
        "npm_run_build": "FAIL (expected until phase 1C)",
        "tests": {
            "exportExcelDashboard": "5/5 PASS",
            "vitest_discovery": "include src/**/*.test.ts(x) unchanged",
        },
        "new_ts_escapes_added": 0,
        "backend_changes": False,
        "recommended_phase2": "DEPLOY-PILOT.1C: B_PROPS_STALE, F_NULLABILITY, I_ROUTE_WORKFLOW, G_ENUM_DRIFT, J_STRICTNESS",
        "writes_executed": True,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Report: {OUT}")
    print(f"Errors: {BEFORE} -> {total} ({report['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
