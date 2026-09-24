#!/usr/bin/env python
"""
DEPLOY-PILOT.1A — Diagnóstico de errores TypeScript que bloquean npm run build.

Uso:
  cd Backend
  python scripts/deploy_pilot_1a_typescript_build_diag.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = REPO_ROOT / "Frontend"
LOG_PATH = BACKEND_ROOT / "scripts/output/deploy_pilot_1a_tsc_build_full.log"
OUTPUT_PATH = BACKEND_ROOT / "scripts/output/deploy_pilot_1a_typescript_build_diag_20260922.json"

ERROR_LINE_RE = re.compile(
    r"^(?P<file>src/[^:]+)\((?P<line>\d+),(?P<col>\d+)\): error (?P<code>TS\d+): (?P<message>.+)$"
)

RECENT_KEYWORDS = {
    "OT-AUTO": ["secuencia", "orden_trabajo", "otSecuencia", "MapaOtSecuencia", "rutaPublicar"],
    "PERF-DASH": ["pendientes", "DashboardExport", "exportExcelDashboard", "indicadores"],
    "ACT-HIST": ["act_hist", "actHist", "documentacion", "materializacion"],
    "COMPROBACIONES": ["comprobacion", "Comprobacion", "actasComprobacion"],
    "RUTAS": ["RutasTrabajo", "rutaPublicar", "operRuta", "planificacion"],
    "REINSPECCION": ["reinspeccion", "Reinspeccion", "notificacion"],
}


@dataclass
class TsError:
    file: str
    line: int
    col: int
    code: str
    message: str
    project: str = "app"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_build_capture() -> str:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(FRONTEND_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    LOG_PATH.write_text(out, encoding="utf-8")
    return out


def _parse_errors(log_text: str) -> list[TsError]:
    errors: list[TsError] = []
    for line in log_text.splitlines():
        m = ERROR_LINE_RE.match(line.strip())
        if not m:
            continue
        errors.append(
            TsError(
                file=m.group("file"),
                line=int(m.group("line")),
                col=int(m.group("col")),
                code=m.group("code"),
                message=m.group("message"),
            )
        )
    return errors


def _is_test_file(path: str) -> bool:
    name = Path(path).name.lower()
    return ".test." in name or ".spec." in name or name.endswith(".test.ts") or name.endswith(".test.tsx")


def _file_bucket(path: str) -> str:
    if _is_test_file(path):
        return "tests_in_src"
    if path.startswith("src/api/"):
        return "api"
    if path.startswith("src/utils/"):
        return "utils"
    if "/Components/" in path or path.endswith(".tsx"):
        return "components"
    if path.startswith("src/Containers/"):
        parts = path.split("/")
        if len(parts) >= 3:
            return f"containers/{parts[2]}"
        return "containers"
    if path.startswith("src/types/"):
        return "types"
    if path.startswith("src/ui/"):
        return "ui"
    return "other"


def _classify_error(err: TsError) -> tuple[str, str, str]:
    """Return (category, severity, regression_tag)."""
    f, msg, code = err.file, err.message, err.code
    lower = f"{f} {msg}".lower()

    if _is_test_file(f):
        return "D_TEST_BUILD_SCOPE", "P3", "CONFIGURATION_NOISE"

    if code == "TS1261" or "differs from file name" in msg and "casing" in msg:
        return "K_CONFIG", "P0", "CONFIGURATION_NOISE"

    if code == "TS2300" and "duplicate identifier" in msg.lower():
        if "esquina_catalogo_id" in msg or "esquina_catalogo_id" in f:
            return "A_API_TYPES_STALE", "P0", "RECENT_REGRESSION"
        return "E_IMPORT_EXPORT", "P0", "PREEXISTING_DEBT"

    if code in ("TS2353",) and "does not exist in type" in msg:
        if any(k in lower for k in ("pendientes", "motivoq", "dashboardexport", "historialnotificacion")):
            return "A_API_TYPES_STALE", "P0", "RECENT_REGRESSION"
        if "comprobacion" in lower or "actuacion" in lower or "ruta" in lower:
            return "A_API_TYPES_STALE", "P1", "RECENT_REGRESSION"
        return "A_API_TYPES_STALE", "P1", "PREEXISTING_DEBT"

    if code == "TS2339" and "does not exist on type" in msg:
        if any(k in lower for k in ("irelevamiento", "inspector", "direccion", "pendientes")):
            return "A_API_TYPES_STALE", "P0", "RECENT_REGRESSION"
        if "mrt" in lower or "material" in f.lower():
            return "H_GENERIC_MRT", "P1", "PREEXISTING_DEBT"
        if "ruta" in lower or "ot" in lower or "secuencia" in lower:
            return "I_ROUTE_WORKFLOW_REFACTOR", "P1", "RECENT_REGRESSION"
        return "B_PROPS_STALE", "P1", "PREEXISTING_DEBT"

    if code in ("TS2322", "TS2345") and ("null" in msg or "undefined" in msg):
        return "F_NULLABILITY", "P1", "PREEXISTING_DEBT"

    if code == "TS2322" and ("sx" in lower or "sxprops" in lower or "overload" in lower):
        if "dialog" in lower or "backdrop" in lower or "mui" in f.lower():
            return "B_PROPS_STALE", "P0", "PREEXISTING_DEBT"
        return "B_PROPS_STALE", "P1", "PREEXISTING_DEBT"

    if code == "TS2769" and "overload" in msg.lower():
        if "motion" in lower or "framer" in f.lower():
            return "B_PROPS_STALE", "P2", "PREEXISTING_DEBT"
        return "B_PROPS_STALE", "P1", "PREEXISTING_DEBT"

    if code == "TS6133":
        return "J_STRICTNESS", "P3", "CONFIGURATION_NOISE"

    if code == "TS2367":
        return "G_ENUM_DRIFT", "P1", "PREEXISTING_DEBT"

    if code in ("TS2305", "TS2307", "TS2724"):
        return "E_IMPORT_EXPORT", "P0", "PREEXISTING_DEBT"

    if code == "TS2783":
        return "J_STRICTNESS", "P3", "CONFIGURATION_NOISE"

    if "mrt" in f.lower() or "material-react-table" in lower:
        return "H_GENERIC_MRT", "P1", "PREEXISTING_DEBT"

    if any(k in f for k in ("RutasTrabajo", "CompletarTrabajos", "ActasComprobacion", "secuencia")):
        return "I_ROUTE_WORKFLOW_REFACTOR", "P1", "RECENT_REGRESSION"

    if code in ("TS2322", "TS2345"):
        return "B_PROPS_STALE", "P1", "PREEXISTING_DEBT"

    return "L_OTHER", "P2", "PREEXISTING_DEBT"


def _concentration(file_counts: Counter) -> dict[str, int | float]:
    if not file_counts:
        return {"files_for_50pct": 0, "files_for_80pct": 0, "files_for_90pct": 0}
    total = sum(file_counts.values())
    cumulative = 0
    files_50 = files_80 = files_90 = 0
    for i, (_, count) in enumerate(file_counts.most_common(), start=1):
        cumulative += count
        if files_50 == 0 and cumulative >= total * 0.5:
            files_50 = i
        if files_80 == 0 and cumulative >= total * 0.8:
            files_80 = i
        if files_90 == 0 and cumulative >= total * 0.9:
            files_90 = i
    return {
        "files_for_50pct": files_50,
        "files_for_80pct": files_80,
        "files_for_90pct": files_90,
        "distinct_files": len(file_counts),
    }


def _count_escapes() -> dict[str, int]:
    patterns = {
        "ts_ignore": re.compile(r"@ts-ignore\b"),
        "ts_expect_error": re.compile(r"@ts-expect-error\b"),
        "as_any": re.compile(r"\bas any\b"),
        "explicit_any": re.compile(r":\s*any\b"),
    }
    counts = {k: 0 for k in patterns}
    for path in (FRONTEND_ROOT / "src").rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for key, pat in patterns.items():
            counts[key] += len(pat.findall(text))
    return counts


def _root_cause_aggregates(errors: list[TsError]) -> list[dict]:
    by_cat: dict[str, list[TsError]] = defaultdict(list)
    for e in errors:
        cat, _, _ = _classify_error(e)
        by_cat[cat].append(e)

    causes: list[dict] = []
    cat_labels = {
        "A_API_TYPES_STALE": "Tipos/DTO frontend desactualizados vs contrato actual",
        "B_PROPS_STALE": "Props MUI/componentes refactorizados (sx, Dialog, overloads)",
        "C_DEAD_CODE": "Código muerto aún typecheckeado",
        "D_TEST_BUILD_SCOPE": "Archivos *.test.* incluidos en tsconfig.app include=src",
        "E_IMPORT_EXPORT": "Imports/exports/duplicados/casing",
        "F_NULLABILITY": "string|null|undefined tras refactors",
        "G_ENUM_DRIFT": "Comparaciones de roles/enums imposibles",
        "H_GENERIC_MRT": "Material React Table / generics",
        "I_ROUTE_WORKFLOW_REFACTOR": "OT, rutas, comprobaciones, workflow",
        "J_STRICTNESS": "noUnusedLocals / duplicados en objetos test",
        "K_CONFIG": "tsconfig / casing archivos",
        "L_OTHER": "Otros",
    }

    for cat_id, items in sorted(by_cat.items(), key=lambda x: -len(x[1])):
        files = sorted({e.file for e in items})
        sev = Counter(_classify_error(e)[1] for e in items).most_common(1)[0][0]
        reg = Counter(_classify_error(e)[2] for e in items).most_common(1)[0][0]
        sample_msgs = list(dict.fromkeys(e.message for e in items))[:5]
        causes.append(
            {
                "id": cat_id,
                "category": cat_labels.get(cat_id, cat_id),
                "files": files[:25],
                "file_count": len(files),
                "error_count": len(items),
                "estimated_cascade": len(items),
                "severity": sev,
                "regression": reg,
                "sample_messages": sample_msgs,
                "recommended_fix": _recommended_fix(cat_id),
            }
        )
    return causes


def _recommended_fix(cat_id: str) -> str:
    fixes = {
        "A_API_TYPES_STALE": "Actualizar interfaces en src/api y types al contrato backend vigente; eliminar campos duplicados en tipos.",
        "B_PROPS_STALE": "Alinear props MUI v7/Dialog wrapper (ConfirmDialog, sx arrays); framer-motion children typing.",
        "C_DEAD_CODE": "Eliminar o excluir módulos sin consumers del grafo de build.",
        "D_TEST_BUILD_SCOPE": "Excluir **/*.test.* de tsconfig.app.json; mantener vitest con tsconfig separado.",
        "E_IMPORT_EXPORT": "Unificar imports Local.d.ts casing; resolver duplicate identifier en API types.",
        "F_NULLABILITY": "Normalizar null guards o tipos opcionales en validations/utils.",
        "G_ENUM_DRIFT": "Corregir narrowing de AppRole en auth/roles.ts.",
        "H_GENERIC_MRT": "Ajustar generics MRT column defs o tipos de tabla.",
        "I_ROUTE_WORKFLOW_REFACTOR": "Sincronizar tipos de rutas/OT/comprobaciones post-refactor.",
        "J_STRICTNESS": "Quitar unused imports/vars o relajar noUnusedLocals solo si se decide.",
        "K_CONFIG": "Renombrar local.d.ts vs Local.d.ts; forceConsistentCasingInFileNames.",
        "L_OTHER": "Revisar caso a caso.",
    }
    return fixes.get(cat_id, "Revisar manualmente.")


def _dead_code_candidates(errors: list[TsError]) -> list[dict]:
    candidates = [
        "saveOtItem",
        "exportExcelDashboard",
        "validations.ts IRelevamiento",
        "Local.d.ts / locales-test",
        "CrudFormErrorSummary unused in crudDialog.test",
    ]
    found = []
    for name in candidates:
        matching = [e.file for e in errors if name.lower().replace(" ", "") in e.file.lower() + e.message.lower()]
        if matching:
            found.append({"symbol_or_area": name, "error_files": sorted(set(matching))[:10]})
    return found


def _recommended_fix_order(causes: list[dict]) -> list[dict]:
    phases = [
        {
            "phase": "TS-FIX.1",
            "focus": "P0 root causes",
            "targets": [c["id"] for c in causes if c["severity"] == "P0"],
        },
        {
            "phase": "TS-FIX.2",
            "focus": "API/types/product code P1",
            "targets": [c["id"] for c in causes if c["severity"] == "P1" and c["id"] not in ("D_TEST_BUILD_SCOPE",)],
        },
        {
            "phase": "TS-FIX.3",
            "focus": "dead code / test scope / strictness P3",
            "targets": ["D_TEST_BUILD_SCOPE", "J_STRICTNESS", "C_DEAD_CODE"],
        },
        {
            "phase": "TS-FIX.4",
            "focus": "build verification",
            "targets": ["npm run build exit 0"],
        },
    ]
    total = sum(c["error_count"] for c in causes)
    remaining = total
    estimates = []
    for phase in phases:
        removed = sum(
            c["error_count"]
            for c in causes
            if c["id"] in phase["targets"] or c["severity"] in phase.get("severities", [])
        )
        if phase["phase"] == "TS-FIX.2":
            removed = sum(c["error_count"] for c in causes if c["id"] in phase["targets"])
        if phase["phase"] == "TS-FIX.3":
            removed = sum(
                c["error_count"]
                for c in causes
                if c["id"] in ("D_TEST_BUILD_SCOPE", "J_STRICTNESS", "C_DEAD_CODE")
            )
        if phase["phase"] == "TS-FIX.4":
            removed = 0
        remaining = max(0, remaining - removed) if phase["phase"] != "TS-FIX.4" else 0
        estimates.append(
            {
                **phase,
                "estimated_errors_removed": removed,
                "estimated_errors_remaining_after": remaining if phase["phase"] != "TS-FIX.4" else 0,
            }
        )
    return estimates


def main() -> int:
    if LOG_PATH.exists():
        log_text = LOG_PATH.read_text(encoding="utf-8", errors="replace")
        if "error TS" not in log_text:
            log_text = _run_build_capture()
    else:
        log_text = _run_build_capture()

    errors = _parse_errors(log_text)
    if not errors:
        print("No se encontraron errores TS en el log; re-ejecutando build...")
        log_text = _run_build_capture()
        errors = _parse_errors(log_text)

    by_code = Counter(e.code for e in errors)
    by_file = Counter(e.file for e in errors)
    by_bucket = Counter(_file_bucket(e.file) for e in errors)
    test_errors = [e for e in errors if _is_test_file(e.file)]
    prod_errors = [e for e in errors if not _is_test_file(e.file)]

    regression_tags = Counter(_classify_error(e)[2] for e in errors)

    causes = _root_cause_aggregates(errors)
    fix_order = _recommended_fix_order(causes)

    tsconfig_scope_static = {
        "root": {"references": ["./tsconfig.app.json", "./tsconfig.node.json"]},
        "app": {
            "include": ["src"],
            "exclude": None,
            "strict": True,
            "noUnusedLocals": True,
            "noUnusedParameters": True,
        },
        "node": {"include": ["vite.config.ts"]},
    }

    test_files_in_src = sum(1 for p in (FRONTEND_ROOT / "src").rglob("*") if _is_test_file(str(p.relative_to(FRONTEND_ROOT)).replace("\\", "/")))

    report = {
        "ticket": "DEPLOY-PILOT.1A",
        "date": "2026-09-22",
        "generated_at": _utc_now(),
        "status": "DIAG_COMPLETE",
        "writes_executed": False,
        "build_command": "tsc -b && vite build",
        "vite_build_isolated": "PASS (documented DEPLOY-PILOT.1)",
        "tsc_build": "FAIL",
        "total_errors": len(errors),
        "errors_by_code": dict(by_code.most_common()),
        "errors_by_file_top30": dict(by_file.most_common(30)),
        "errors_by_bucket": dict(by_bucket.most_common()),
        "file_concentration": _concentration(by_file),
        "tsconfig_scope": {
            **tsconfig_scope_static,
            "production_typechecks": ["src/** (all under src, no exclude)"],
            "test_files_under_src_count": test_files_in_src,
            "errors_in_test_files": len(test_errors),
            "errors_in_product_code": len(prod_errors),
            "test_scope_finding": (
                f"{len(test_errors)} errores ({100*len(test_errors)/max(len(errors),1):.1f}%) "
                f"provienen de {len({e.file for e in test_errors})} archivos *.test.* incluidos "
                "por tsconfig.app.json include=[\"src\"]. Vitest corre aparte; excluir tests del "
                "build productivo es corrección de config válida (no aplicada en este ticket)."
            ),
        },
        "root_causes": causes,
        "recent_vs_preexisting": {
            "RECENT_REGRESSION": regression_tags.get("RECENT_REGRESSION", 0),
            "PREEXISTING_DEBT": regression_tags.get("PREEXISTING_DEBT", 0),
            "CONFIGURATION_NOISE": regression_tags.get("CONFIGURATION_NOISE", 0),
            "known_recent_areas": RECENT_KEYWORDS,
        },
        "dead_code_candidates": _dead_code_candidates(errors),
        "test_scope_findings": {
            "tests_in_build_scope": True,
            "test_error_count": len(test_errors),
            "top_test_files": dict(Counter(e.file for e in test_errors).most_common(15)),
        },
        "api_contract_findings": [
            {
                "area": "esquina_catalogo_id duplicate",
                "files": ["src/api/actuacionesPendientesApi.ts", "src/api/relevamientosPendientesApi.ts"],
                "codes": ["TS2300"],
            },
            {
                "area": "DashboardExportPayload.pendientes removed (PERF-DASH.2)",
                "files": ["src/utils/exportExcelDashboard.ts", "src/utils/exportExcelDashboard.test.ts"],
                "codes": ["TS2339", "TS2353"],
            },
            {
                "area": "IRelevamiento fields inspector/direccion",
                "files": ["src/utils/validations.ts"],
                "codes": ["TS2339", "TS2345"],
            },
            {
                "area": "HistorialNotificacionFiltroPayload.motivoQ",
                "files": ["src/api/notificacionesExportApi.test.ts"],
                "codes": ["TS2353"],
            },
        ],
        "escape_hatches_existing": _count_escapes(),
        "escape_hatches_added": 0,
        "recommended_fix_order": fix_order,
        "log_path": str(LOG_PATH),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Report: {OUTPUT_PATH}")
    print(f"Total errors: {len(errors)}")
    print(f"Test file errors: {len(test_errors)} / Product: {len(prod_errors)}")
    print(f"Top codes: {by_code.most_common(5)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
