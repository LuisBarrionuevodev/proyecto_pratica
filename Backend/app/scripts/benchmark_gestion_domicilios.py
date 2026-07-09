"""
PR6C.1 — Benchmark formal de GET /map/pendientes (Gestión Domicilios).

Uso:
    cd Backend
    python -m app.scripts.benchmark_gestion_domicilios
    python -m app.scripts.benchmark_gestion_domicilios --csv > benchmark.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Any

from app import create_app
from app.domains.geolocalizacion.geocode.services.gestion_domicilios_service import (
    get_last_gestion_domicilios_perf,
    list_gestion_domicilios,
)
from app.domains.geolocalizacion.geocode.schemas.gestion_domicilios_query import (
    GestionDomiciliosQuery,
)
from app.domains.geolocalizacion.geocode.services.map_service import (
    get_last_pendientes_perf,
    list_pendientes,
)

BENCHMARK_CASES: list[dict[str, Any]] = [
    {"endpoint": "/map/pendientes", "params": {}, "kind": "pendientes"},
    {"endpoint": "/map/pendientes", "params": {"slice": "nomenclatura_pendiente"}, "kind": "pendientes"},
    {"endpoint": "/map/pendientes", "params": {"slice": "geo_pendiente"}, "kind": "pendientes"},
    {"endpoint": "/map/pendientes", "params": {"slice": "baja_confianza"}, "kind": "pendientes"},
    {"endpoint": "/map/pendientes", "params": {"slice": "ok"}, "kind": "pendientes"},
    {"endpoint": "/map/pendientes", "params": {"slice": "validado_manual"}, "kind": "pendientes"},
    {"endpoint": "/map/pendientes", "params": {"slice": "error"}, "kind": "pendientes"},
    {"endpoint": "/map/pendientes", "params": {"slice": "all"}, "kind": "pendientes"},
    {
        "endpoint": "/map/gestion-domicilios",
        "params": {"status_operativo": "requiere_accion", "page": "1", "page_size": "50"},
        "kind": "gestion",
    },
    {
        "endpoint": "/map/gestion-domicilios",
        "params": {"status_operativo": "todos", "page": "1", "page_size": "50"},
        "kind": "gestion",
    },
    {
        "endpoint": "/map/gestion-domicilios",
        "params": {"status_operativo": "sin_punto", "page": "1", "page_size": "50"},
        "kind": "gestion",
    },
]


def _params_label(params: dict[str, Any]) -> str:
    if not params:
        return ""
    return "&".join(f"{k}={v}" for k, v in sorted(params.items()))


def run_benchmark() -> list[dict[str, Any]]:
    """
    Ejecuta casos de benchmark contra ``list_pendientes``.

    Retorno:
        Lista de filas con métricas por caso.
    """
    rows: list[dict[str, Any]] = []
    for case in BENCHMARK_CASES:
        params = case["params"]
        kind = case.get("kind", "pendientes")
        if kind == "gestion":
            q = GestionDomiciliosQuery.from_request_args(params)
            list_gestion_domicilios(q)
            perf_g = get_last_gestion_domicilios_perf()
            rows.append(
                {
                    "endpoint": case["endpoint"],
                    "params": _params_label(params),
                    "rows_sql": perf_g.rows_sql,
                    "rows_response": perf_g.rows_response,
                    "classified_count": 0,
                    "match_count": 0,
                    "elapsed_ms": round(perf_g.total_ms, 1),
                }
            )
            continue

        list_pendientes(
            desde=params.get("desde"),
            hasta=params.get("hasta"),
            scope=params.get("scope"),
            kind=params.get("kind"),
            slice=params.get("slice"),
        )
        perf = get_last_pendientes_perf()
        rows.append(
            {
                "endpoint": case["endpoint"],
                "params": _params_label(params),
                "rows_sql": perf.rows_sql,
                "rows_response": perf.rows_response,
                "classified_count": perf.classified_count,
                "match_count": perf.match_count,
                "elapsed_ms": round(perf.total_ms, 1),
            }
        )
    return rows


def _print_table(rows: list[dict[str, Any]]) -> None:
    headers = [
        "endpoint",
        "params",
        "rows_sql",
        "rows_response",
        "classified_count",
        "match_count",
        "elapsed_ms",
    ]
    widths = {h: max(len(h), *(len(str(r.get(h, ""))) for r in rows)) for h in headers}
    line = "  ".join(h.ljust(widths[h]) for h in headers)
    print(line)
    print("-" * len(line))
    for row in rows:
        print("  ".join(str(row[h]).ljust(widths[h]) for h in headers))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark Gestión Domicilios /map/pendientes")
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Salida CSV en stdout (sin encabezados decorativos).",
    )
    args = parser.parse_args(argv)

    os.environ.setdefault("PERF_LOG", "1")

    app = create_app()
    with app.app_context():
        rows = run_benchmark()

    if args.csv:
        writer = csv.DictWriter(
            sys.stdout,
            fieldnames=[
                "endpoint",
                "params",
                "rows_sql",
                "rows_response",
                "classified_count",
                "match_count",
                "elapsed_ms",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    else:
        print("PR6C.1 benchmark — Gestión Domicilios (/map/pendientes)")
        print(f"PERF_LOG={os.environ.get('PERF_LOG', '')}")
        _print_table(rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
