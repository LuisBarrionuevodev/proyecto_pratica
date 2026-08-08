"""
IND-BE.1 — Benchmark de endpoints de indicadores (diagnóstico de performance).

Uso:
    cd Backend
    set PERF_LOG=1
    set PYTHONPATH=.
    python -m app.scripts.benchmark_indicadores_perf

Con distrito/inspector concretos:
    python -m app.scripts.benchmark_indicadores_perf --distrito-id 3 --inspector-id 5
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from typing import Any, Optional

from app import create_app
from app.domains.indicadores.services.indicadores_ejecutivo_service import (
    build_indicadores_ejecutivo,
)
from app.domains.indicadores.services.indicadores_no_realizadas_service import (
    build_indicadores_no_realizadas,
)
from app.domains.indicadores.services.indicadores_pendientes_service import (
    build_indicadores_pendientes,
)
from app.domains.indicadores.services.indicadores_productividad_service import (
    build_indicadores_productividad,
)
from app.domains.indicadores.services.indicadores_riesgo_service import build_indicadores_riesgo
from app.domains.indicadores.utils.indicadores_perf_log import PerfTimer, log_indicadores_endpoint

logging.basicConfig(level=logging.INFO, format="%(message)s")

BUILDERS: dict[str, Any] = {
    "ejecutivo": build_indicadores_ejecutivo,
    "pendientes": build_indicadores_pendientes,
    "riesgo": build_indicadores_riesgo,
    "no-realizadas": build_indicadores_no_realizadas,
    "productividad": build_indicadores_productividad,
}


def _today() -> date:
    return date.today()


def _mensual_range(ref: date) -> tuple[date, date]:
    desde = ref.replace(day=1)
    if ref.month == 12:
        hasta = date(ref.year, 12, 31)
    else:
        hasta = date(ref.year, ref.month + 1, 1) - timedelta(days=1)
    return desde, hasta


def _trimestral_range(ref: date) -> tuple[date, date]:
    q_start_month = ((ref.month - 1) // 3) * 3 + 1
    desde = date(ref.year, q_start_month, 1)
    end_month = q_start_month + 2
    if end_month == 12:
        hasta = date(ref.year, 12, 31)
    else:
        hasta = date(ref.year, end_month + 1, 1) - timedelta(days=1)
    return desde, hasta


def _anual_range(ref: date) -> tuple[date, date]:
    return date(ref.year, 1, 1), date(ref.year, 12, 31)


def _scenario_cases(
    *,
    distrito_id: Optional[int],
    inspector_id: Optional[int],
) -> list[dict[str, Any]]:
    ref = _today()
    mensual = _mensual_range(ref)
    trimestral = _trimestral_range(ref)
    anual = _anual_range(ref)
    return [
        {
            "label": "trimestral_todos",
            "desde": trimestral[0],
            "hasta": trimestral[1],
            "distrito_id": None,
            "inspector_id": None,
        },
        {
            "label": "mensual_todos",
            "desde": mensual[0],
            "hasta": mensual[1],
            "distrito_id": None,
            "inspector_id": None,
        },
        {
            "label": "anual_todos",
            "desde": anual[0],
            "hasta": anual[1],
            "distrito_id": None,
            "inspector_id": None,
        },
        {
            "label": "mensual_distrito",
            "desde": mensual[0],
            "hasta": mensual[1],
            "distrito_id": distrito_id,
            "inspector_id": None,
        },
        {
            "label": "mensual_inspector",
            "desde": mensual[0],
            "hasta": mensual[1],
            "distrito_id": None,
            "inspector_id": inspector_id,
        },
    ]


def _run_case(case: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for endpoint, builder in BUILDERS.items():
        timer = PerfTimer()
        builder(
            case["desde"],
            case["hasta"],
            case["distrito_id"],
            case["inspector_id"],
        )
        total_ms = timer.elapsed_ms()
        log_indicadores_endpoint(
            endpoint,
            total_ms=total_ms,
            desde=case["desde"],
            hasta=case["hasta"],
            distrito_id=case["distrito_id"],
            inspector_id=case["inspector_id"],
            scenario=case["label"],
        )
        rows.append(
            {
                "scenario": case["label"],
                "endpoint": endpoint,
                "total_ms": round(total_ms, 1),
                "desde": case["desde"].isoformat(),
                "hasta": case["hasta"].isoformat(),
                "distrito_id": case["distrito_id"],
                "inspector_id": case["inspector_id"],
            }
        )
    return rows


def run_benchmark(
    *,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Ejecuta los 5 escenarios × 5 endpoints y devuelve filas de tiempos."""
    out: list[dict[str, Any]] = []
    for case in _scenario_cases(distrito_id=distrito_id, inspector_id=inspector_id):
        if case["label"] == "mensual_distrito" and distrito_id is None:
            continue
        if case["label"] == "mensual_inspector" and inspector_id is None:
            continue
        out.extend(_run_case(case))
    return out


def _print_table(rows: list[dict[str, Any]]) -> None:
    print("scenario\tendpoint\ttotal_ms\tdesde\thasta\tdistrito\tinspector")
    for row in rows:
        print(
            f"{row['scenario']}\t{row['endpoint']}\t{row['total_ms']}\t"
            f"{row['desde']}\t{row['hasta']}\t{row['distrito_id']}\t{row['inspector_id']}"
        )

    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_scenario.setdefault(row["scenario"], []).append(row)
    print("\nResumen (endpoint más lento por escenario):")
    for scenario, scenario_rows in by_scenario.items():
        slowest = max(scenario_rows, key=lambda r: r["total_ms"])
        print(
            f"  {scenario}: más lento={slowest['endpoint']} ({slowest['total_ms']}ms)"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark indicadores IND-BE.1")
    parser.add_argument("--distrito-id", type=int, default=None)
    parser.add_argument("--inspector-id", type=int, default=None)
    args = parser.parse_args(argv)

    os.environ.setdefault("PERF_LOG", "1")
    app = create_app()
    with app.app_context():
        rows = run_benchmark(
            distrito_id=args.distrito_id,
            inspector_id=args.inspector_id,
        )
    _print_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
