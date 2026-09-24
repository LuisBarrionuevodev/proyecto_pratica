"""
PERF-DASH.2 — Runner post-eliminación Pendientes + optimizaciones KPI restantes.
Uso: cd Backend && set PYTHONPATH=. && python scripts/perf_dash_2_remove_pendientes_optimize_remaining_runner.py
"""

from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import event

from app import create_app
from app.database import db
from app.domains.indicadores.services.indicadores_ejecutivo_service import (
    build_indicadores_ejecutivo,
)
from app.domains.indicadores.services.indicadores_no_realizadas_service import (
    build_indicadores_no_realizadas,
)
from app.domains.indicadores.services.indicadores_productividad_service import (
    build_indicadores_productividad,
)
from app.domains.indicadores.services.indicadores_resumen_service import (
    build_indicadores_resumen,
)
from app.domains.indicadores.services.indicadores_riesgo_service import (
    build_indicadores_riesgo,
)

OUTPUT = (
    Path(__file__).resolve().parent
    / "output"
    / "perf_dash_2_remove_pendientes_optimize_remaining_20260921.json"
)
PERF_DASH_1 = (
    Path(__file__).resolve().parent / "output" / "perf_dash_1_diag_20260921.json"
)

BASELINE_DESDE = date(2026, 9, 1)
BASELINE_HASTA = date(2026, 9, 21)

BASELINE_KPIS = {
    "actuaciones_realizadas": 17,
    "actas_labradas": 35,
    "inspecciones_realizadas": 9,
    "reinspecciones_notificacion_realizadas": 1,
    "reinspecciones_oficio_realizadas": 4,
    "ratificaciones_clausura_realizadas": 0,
    "ratificaciones_decomiso_realizadas": 1,
    "verificar_informar_realizadas": 3,
    "mercaderia_decomisada_kg": 16316.0,
    "actas_por_tipo": {
        "inspeccion": 13,
        "notificacion": 10,
        "comprobacion": 8,
        "clausura": 2,
        "decomiso": 2,
    },
}


def _normalize_sql(sql: str) -> str:
    s = re.sub(r"\s+", " ", sql.strip().lower())
    s = re.sub(r"\b\d+\b", "?", s)
    return s[:240]


class QueryCounter:
    def __init__(self) -> None:
        self.queries: list[dict[str, Any]] = []

    def attach(self) -> None:
        @event.listens_for(db.engine, "before_cursor_execute")
        def before(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
            context._perf_start = time.perf_counter()

        @event.listens_for(db.engine, "after_cursor_execute")
        def after(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
            elapsed = (
                time.perf_counter() - getattr(context, "_perf_start", time.perf_counter())
            ) * 1000
            self.queries.append(
                {
                    "sql_norm": _normalize_sql(statement),
                    "duration_ms": round(elapsed, 2),
                }
            )


def _run_builder(builder, desde: date, hasta: date, distrito_id=None, inspector_id=None):
    qc = QueryCounter()
    qc.attach()
    t0 = time.perf_counter()
    result = builder(desde, hasta, distrito_id, inspector_id)
    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "total_ms": total_ms,
        "query_count": len(qc.queries),
        "payload": result.model_dump(mode="json") if hasattr(result, "model_dump") else result,
    }


def _load_perf_dash_1() -> dict[str, Any]:
    if PERF_DASH_1.is_file():
        return json.loads(PERF_DASH_1.read_text(encoding="utf-8"))
    return {}


def _count_fetch_visita_rows_calls() -> int:
    from unittest.mock import patch

    from app.domains.indicadores.services import indicadores_no_realizadas_service as svc

    calls = 0
    real = svc.fetch_no_realizadas_visita_rows

    def tracked(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real(*args, **kwargs)

    with patch.object(svc, "fetch_no_realizadas_visita_rows", side_effect=tracked):
        build_indicadores_no_realizadas(BASELINE_DESDE, BASELINE_HASTA)
    return calls


def main() -> None:
    app = create_app()
    with app.app_context():
        builders = {
            "ejecutivo": build_indicadores_ejecutivo,
            "riesgo": build_indicadores_riesgo,
            "no-realizadas": build_indicadores_no_realizadas,
            "productividad": build_indicadores_productividad,
        }

        after_timings: dict[str, dict[str, Any]] = {}
        after_payloads: dict[str, Any] = {}
        for name, builder in builders.items():
            run = _run_builder(builder, BASELINE_DESDE, BASELINE_HASTA)
            after_timings[name] = {
                "total_ms": run["total_ms"],
                "query_count": run["query_count"],
            }
            after_payloads[name] = run["payload"]

        total_queries = sum(t["query_count"] for t in after_timings.values())
        total_ms_parallel = max(t["total_ms"] for t in after_timings.values())
        total_ms_serial = sum(t["total_ms"] for t in after_timings.values())

        ejecutivo_after = after_payloads["ejecutivo"]
        kpis_after = ejecutivo_after.get("kpis", {})
        actas_after = ejecutivo_after.get("actas_por_tipo", {})

        correctness_equal = (
            kpis_after.get("actuaciones_realizadas") == BASELINE_KPIS["actuaciones_realizadas"]
            and kpis_after.get("actas_labradas") == BASELINE_KPIS["actas_labradas"]
            and actas_after == BASELINE_KPIS["actas_por_tipo"]
            and kpis_after.get("reinspecciones_notificacion_realizadas")
            == BASELINE_KPIS["reinspecciones_notificacion_realizadas"]
            and kpis_after.get("reinspecciones_oficio_realizadas")
            == BASELINE_KPIS["reinspecciones_oficio_realizadas"]
            and kpis_after.get("ratificaciones_clausura_realizadas")
            == BASELINE_KPIS["ratificaciones_clausura_realizadas"]
            and kpis_after.get("ratificaciones_decomiso_realizadas")
            == BASELINE_KPIS["ratificaciones_decomiso_realizadas"]
            and kpis_after.get("verificar_informar_realizadas")
            == BASELINE_KPIS["verificar_informar_realizadas"]
            and float(kpis_after.get("mercaderia_decomisada_kg", -1))
            == BASELINE_KPIS["mercaderia_decomisada_kg"]
        )

        fetch_visita_calls = _count_fetch_visita_rows_calls()

        dash1 = _load_perf_dash_1()
        dash1_timings = dash1.get("backend", {}).get(
            "endpoint_timings", dash1.get("endpoint_timings", {})
        ).get("mensual_sin_filtros", dash1.get("endpoint_timings", {}).get("mensual_sin_filtros", {}))
        dash1_query_counts = dash1.get("backend", {}).get(
            "query_counts", dash1.get("query_counts", {})
        )

        before_dashboard_queries = sum(
            dash1_timings.get(k, {}).get("query_count", 0)
            for k in ("ejecutivo", "pendientes", "riesgo", "no-realizadas", "productividad")
        )
        before_dashboard_ms = max(
            (
                dash1_timings.get(k, {}).get("total_ms", 0)
                for k in ("ejecutivo", "pendientes", "riesgo", "no-realizadas", "productividad")
            ),
            default=8889.6,
        )

        resumen_run = _run_builder(
            build_indicadores_resumen, BASELINE_DESDE, BASELINE_HASTA
        )

        report = {
            "ticket": "PERF-DASH.2",
            "date": "2026-09-21",
            "writes_executed": False,
            "migration_required": False,
            "pendientes": {
                "frontend_removed": True,
                "backend_endpoint_removed": True,
                "exclusive_code_removed": True,
                "other_workflows_untouched": True,
                "consumer_audit": "DASHBOARD_ONLY (Panel + tests + benchmark + diag runner)",
            },
            "remaining_kpis_baseline": {
                "periodo": {
                    "desde": BASELINE_DESDE.isoformat(),
                    "hasta": BASELINE_HASTA.isoformat(),
                },
                "ejecutivo": BASELINE_KPIS,
            },
            "remaining_kpis_after": {
                "ejecutivo": {
                    "kpis": kpis_after,
                    "actas_por_tipo": actas_after,
                },
                "riesgo": after_payloads.get("riesgo"),
                "no_realizadas": after_payloads.get("no-realizadas"),
                "productividad": after_payloads.get("productividad"),
            },
            "correctness_equal": correctness_equal,
            "no_realizadas_optimization": {
                "fetch_no_realizadas_visita_rows_calls_per_request": fetch_visita_calls,
                "target_calls": 1,
                "before_duplicate_fetch_evidence": "PERF-DASH.1: visita_rows SQL duplicated 2x in no-realizadas",
                "after_query_count": after_timings["no-realizadas"]["query_count"],
                "before_query_count": dash1_timings.get("no-realizadas", {}).get("query_count", 4),
            },
            "actas_optimization": {
                "description": "_count_actas_labradas consolidated to single SELECT with scalar subqueries",
                "after_ejecutivo_query_count": after_timings["ejecutivo"]["query_count"],
                "before_ejecutivo_query_count": dash1_timings.get("ejecutivo", {}).get("query_count", 9),
            },
            "riesgo_optimization": {
                "description": "actuacion_ids_realizadas_subquery materialized once and passed to motivo/decomiso queries",
                "after_query_count": after_timings["riesgo"]["query_count"],
                "before_query_count": dash1_timings.get("riesgo", {}).get("query_count", 4),
            },
            "productividad_changes": {
                "description": "No aggressive refactor; preserved groupings",
                "after_query_count": after_timings["productividad"]["query_count"],
                "before_query_count": dash1_timings.get("productividad", {}).get("query_count", 7),
            },
            "frontend_requests_before": {
                "count": 7,
                "breakdown": "2 catalogs + 5 indicadores (incl. pendientes)",
            },
            "frontend_requests_after": {
                "count": 6,
                "breakdown": "2 catalogs + 4 indicadores (ejecutivo, riesgo, no-realizadas, productividad)",
            },
            "backend_query_count_before": {
                "dashboard_indicadores_total": before_dashboard_queries,
                "pendientes_only": dash1_timings.get("pendientes", {}).get("query_count", 12388),
                "note": "From PERF-DASH.1 mensual_sin_filtros",
            },
            "backend_query_count_after": {
                "dashboard_indicadores_total": total_queries,
                "by_endpoint": after_timings,
            },
            "dashboard_timeline_before": {
                "blocking_endpoint": "pendientes",
                "parallel_max_ms": before_dashboard_ms,
                "pendientes_ms": dash1_timings.get("pendientes", {}).get("total_ms", 8889.6),
            },
            "dashboard_timeline_after": {
                "parallel_max_ms": total_ms_parallel,
                "serial_sum_ms": total_ms_serial,
                "note": "4 endpoints; no pendientes blocking",
            },
            "resumen_legacy_status": {
                "endpoint": "GET /api/indicadores/resumen",
                "dashboard_consumer": "DashboardTendenciasSection (not Panel mount); Panel main blocks use split endpoints",
                "measured_query_count": resumen_run["query_count"],
                "measured_ms": resumen_run["total_ms"],
                "action": "NOT_OPTIMIZED — report for future cleanup if no runtime consumers",
            },
            "tests_backend": {
                "focal_suite": "pytest tests/test_indicadores_dashboard_blocks.py tests/test_indicadores_no_realizadas.py tests/test_indicadores_actas_labradas.py tests/test_indicadores_riesgo.py tests/test_indicadores_productividad.py",
                "pendientes_route_absent": "test_indicadores_pendientes_endpoint_removed expects 404",
            },
            "tests_frontend": {
                "focal_suite": "vitest Panel.test.tsx dashboardPdfMappers.test.ts dashboardPdfDocument.test.ts",
                "pendientes_section_absent": "PERF-DASH.2 static test in Panel.test.tsx",
            },
            "manual_qa": {
                "sandbox": "Open Dashboard; verify 4 KPI blocks; no Pendientes tab; period/distrito/inspector filters",
                "writes": False,
            },
            "deferred": {
                "dashboard_pendientes_until_clean_db": True,
                "note": "Do not reintroduce N+1 pendientes endpoint; design set-based when DB clean",
            },
            "status": "PASS" if correctness_equal and fetch_visita_calls == 1 else "FAIL",
        }

        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"\nWrote {OUTPUT}")


if __name__ == "__main__":
    main()
