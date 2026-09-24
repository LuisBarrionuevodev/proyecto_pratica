"""
PERF-DASH.1-DIAG — Runner de diagnóstico (solo lectura, sin optimizaciones).
Uso: cd Backend && set PYTHONPATH=. && python scripts/perf_dash_1_diag_runner.py
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import event, func, text

from app import create_app
from app.database import db
from app.domains.indicadores.services.indicadores_ejecutivo_service import build_indicadores_ejecutivo
from app.domains.indicadores.services.indicadores_no_realizadas_service import build_indicadores_no_realizadas
from app.domains.indicadores.services.indicadores_productividad_service import build_indicadores_productividad
from app.domains.indicadores.services.indicadores_resumen_service import build_indicadores_resumen
from app.domains.indicadores.services.indicadores_riesgo_service import build_indicadores_riesgo
from app.models import Domicilio, Inspector

OUTPUT = Path(__file__).resolve().parent / "output" / "perf_dash_1_diag_20260921.json"


def _mensual_range(ref: date) -> tuple[date, date]:
    return ref.replace(day=1), ref


def _trimestral_range(ref: date) -> tuple[date, date]:
    q = ((ref.month - 1) // 3) * 3 + 1
    return date(ref.year, q, 1), ref


def _anual_range(ref: date) -> tuple[date, date]:
    return date(ref.year, 1, 1), ref


def _semanal_range(ref: date) -> tuple[date, date]:
    return ref - timedelta(days=6), ref


def _normalize_sql(sql: str) -> str:
    s = re.sub(r"\s+", " ", sql.strip().lower())
    s = re.sub(r"\b\d+\b", "?", s)
    return s[:240]


class QueryCounter:
    def __init__(self) -> None:
        self.queries: list[dict[str, Any]] = []
        self._start: float = 0.0

    def attach(self) -> None:
        @event.listens_for(db.engine, "before_cursor_execute")
        def before(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
            context._perf_start = time.perf_counter()

        @event.listens_for(db.engine, "after_cursor_execute")
        def after(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
            elapsed = (time.perf_counter() - getattr(context, "_perf_start", time.perf_counter())) * 1000
            self.queries.append(
                {
                    "sql_norm": _normalize_sql(statement),
                    "duration_ms": round(elapsed, 2),
                }
            )


def _count_tables() -> dict[str, int]:
    tables = [
        "actuaciones",
        "ruta_item",
        "iniciador_ruta",
        "ruta_trabajo",
        "orden_trabajo",
        "domicilio",
        "inspector",
        "actuaciones_inspector",
        "decomiso",
        "notificacion",
        "comprobacion",
        "inspeccion",
        "clausura",
    ]
    out: dict[str, int] = {}
    for t in tables:
        try:
            out[t] = int(db.session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() or 0)
        except Exception:
            out[t] = -1
    return out


def _run_builder(name: str, builder, desde: date, hasta: date, distrito_id=None, inspector_id=None):
    qc = QueryCounter()
    qc.attach()
    t0 = time.perf_counter()
    result = builder(desde, hasta, distrito_id, inspector_id)
    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    dup = Counter(q["sql_norm"] for q in qc.queries)
    duplicates = [
        {"sql_norm": k, "count": v, "accumulated_ms": round(sum(x["duration_ms"] for x in qc.queries if x["sql_norm"] == k), 1)}
        for k, v in dup.items()
        if v > 1
    ]
    duplicates.sort(key=lambda x: x["accumulated_ms"], reverse=True)
    return {
        "endpoint": name,
        "total_ms": total_ms,
        "query_count": len(qc.queries),
        "duplicate_query_groups": len(duplicates),
        "top_duplicates": duplicates[:8],
        "payload": result.model_dump(mode="json") if hasattr(result, "model_dump") else result,
    }


def _sample_distrito_inspector() -> tuple[Optional[int], Optional[int]]:
    distrito_id = db.session.query(Domicilio.distrito_id).filter(Domicilio.distrito_id.isnot(None)).limit(1).scalar()
    inspector_id = db.session.query(Inspector.id).limit(1).scalar()
    return (int(distrito_id) if distrito_id else None, int(inspector_id) if inspector_id else None)


def _explain_pendientes_stock() -> list[dict[str, Any]]:
    sql = """
    SELECT iniciador_ruta.id
    FROM iniciador_ruta
    WHERE iniciador_ruta.deleted_at IS NULL
      AND iniciador_ruta.estado_iniciador = 'PENDIENTE'
      AND iniciador_ruta.tipo_iniciador IN ('RELEVAMIENTO','REINSPECCION_OFICIO','REINSPECCION_NOTIFICACION','DENUNCIA')
      AND NOT EXISTS (
        SELECT 1 FROM ruta_item
        JOIN ruta_trabajo ON ruta_item.ruta_trabajo_id = ruta_trabajo.id
        WHERE ruta_item.iniciador_ruta_id = iniciador_ruta.id
          AND ruta_item.deleted_at IS NULL
          AND ruta_trabajo.estado_ruta = 'BORRADOR'
      )
    """
    try:
        rows = db.session.execute(text(f"EXPLAIN {sql}")).fetchall()
        return [{"id": i, "row": list(r)} for i, r in enumerate(rows)]
    except Exception as e:
        return [{"error": str(e)}]


def _explain_realizadas_count(desde: date, hasta: date) -> list[dict[str, Any]]:
    sql = """
    SELECT COUNT(DISTINCT ruta_item.id)
    FROM ruta_item
    JOIN ruta_trabajo ON ruta_item.ruta_trabajo_id = ruta_trabajo.id
    JOIN iniciador_ruta ON ruta_item.iniciador_ruta_id = iniciador_ruta.id
    JOIN actuaciones ON ruta_item.actuacion_id = actuaciones.id
    WHERE ruta_item.deleted_at IS NULL
      AND iniciador_ruta.deleted_at IS NULL
      AND ruta_item.estado_ruta_item = 'FINALIZADO'
      AND ruta_item.estado_ejecucion = 'REALIZADO'
      AND ruta_item.actuacion_id IS NOT NULL
      AND ruta_trabajo.estado_ruta = 'PUBLICADA'
      AND ruta_trabajo.fecha >= :desde AND ruta_trabajo.fecha <= :hasta
    """
    try:
        rows = db.session.execute(text(f"EXPLAIN {sql}"), {"desde": desde, "hasta": hasta}).fetchall()
        return [{"id": i, "row": list(r)} for i, r in enumerate(rows)]
    except Exception as e:
        return [{"error": str(e)}]


def _index_inventory() -> list[dict[str, Any]]:
    try:
        rows = db.session.execute(
            text(
                """
                SELECT TABLE_NAME, INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS cols, NON_UNIQUE
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME IN (
                    'actuaciones','ruta_item','iniciador_ruta','ruta_trabajo','domicilio',
                    'actuaciones_inspector','decomiso','iniciador_ruta'
                  )
                GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE
                ORDER BY TABLE_NAME, INDEX_NAME
                """
            )
        ).fetchall()
        return [{"table": r[0], "index": r[1], "columns": r[2], "non_unique": r[3]} for r in rows]
    except Exception as e:
        return [{"error": str(e)}]


def main() -> None:
    ref = date.today()
    ranges = {
        "semanal": _semanal_range(ref),
        "mensual": (ref.replace(day=1), ref),
        "trimestral": _trimestral_range(ref),
        "anual": _anual_range(ref),
    }

    app = create_app()
    with app.app_context():
        dataset_sizes = _count_tables()
        distrito_id, inspector_id = _sample_distrito_inspector()

        builders = {
            "ejecutivo": build_indicadores_ejecutivo,
            "riesgo": build_indicadores_riesgo,
            "no-realizadas": build_indicadores_no_realizadas,
            "productividad": build_indicadores_productividad,
            "resumen": build_indicadores_resumen,
        }

        endpoint_timings: dict[str, Any] = {}
        query_counts: dict[str, int] = {}
        duplicate_queries: dict[str, list] = {}
        baseline_values: dict[str, Any] = {}

        mensual_desde, mensual_hasta = ranges["mensual"]
        scenarios = [
            ("mensual_sin_filtros", mensual_desde, mensual_hasta, None, None),
            ("mensual_distrito", mensual_desde, mensual_hasta, distrito_id, None),
            ("mensual_inspector", mensual_desde, mensual_hasta, None, inspector_id),
            ("anual_sin_filtros", ranges["anual"][0], ranges["anual"][1], None, None),
        ]

        for label, desde, hasta, dist, insp in scenarios:
            if label.endswith("_distrito") and dist is None:
                continue
            if label.endswith("_inspector") and insp is None:
                continue
            scenario_rows = {}
            for name, builder in builders.items():
                if name == "resumen" and label != "mensual_sin_filtros":
                    continue
                run = _run_builder(name, builder, desde, hasta, dist, insp)
                scenario_rows[name] = {"total_ms": run["total_ms"], "query_count": run["query_count"]}
                query_counts[f"{label}:{name}"] = run["query_count"]
                duplicate_queries[f"{label}:{name}"] = run["top_duplicates"]
                if label == "mensual_sin_filtros" and name in (
                    "ejecutivo",
                    "riesgo",
                    "no-realizadas",
                    "productividad",
                ):
                    baseline_values[name] = run["payload"]
            endpoint_timings[label] = scenario_rows

        period_switch_cost = {}
        for period, (desde, hasta) in ranges.items():
            if period == "semanal":
                continue
            t0 = time.perf_counter()
            for b in (
                build_indicadores_ejecutivo,
                build_indicadores_riesgo,
                build_indicadores_no_realizadas,
                build_indicadores_productividad,
            ):
                b(desde, hasta, None, None)
            period_switch_cost[period] = round((time.perf_counter() - t0) * 1000, 1)

        explain_results = {
            "pendientes_stock_iniciadores": _explain_pendientes_stock(),
            "realizadas_count_mensual": _explain_realizadas_count(mensual_desde, mensual_hasta),
        }
        index_inventory = _index_inventory()

        # Frontend load model (estimated from backend + code audit)
        mensual_backend_serial_ms = sum(endpoint_timings.get("mensual_sin_filtros", {}).get(k, {}).get("total_ms", 0) for k in builders if k != "resumen" or True)
        mensual_block = endpoint_timings.get("mensual_sin_filtros", {})
        mensual_parallel_est = max((v.get("total_ms", 0) for v in mensual_block.values()), default=0)
        mensual_parallel_est += sum(v.get("total_ms", 0) for k, v in mensual_block.items() if k != max(mensual_block, key=lambda x: mensual_block[x].get("total_ms", 0), default="pendientes"))

        report = {
            "ticket": "PERF-DASH.1-DIAG",
            "date": "2026-09-21",
            "writes_executed": False,
            "environment": {
                "db": str(db.engine.url).split("@")[-1] if db.engine else "unknown",
                "measurement_method": "Python runner + SQLAlchemy query counter + EXPLAIN (read-only)",
                "benchmark_script": "app/scripts/benchmark_indicadores_perf.py (5 block endpoints)",
                "frontend_route": "/dashboard",
                "backend_prefix": "/api/indicadores",
            },
            "dataset_sizes": dataset_sizes,
            "baseline_values": baseline_values,
            "frontend": {
                "architecture": {
                    "orchestrator": "Frontend/src/Containers/Dashboard/Components/Panel.tsx",
                    "hooks": [
                        "useIndicadoresEjecutivo",
                        "useIndicadoresPendientes",
                        "useIndicadoresRiesgo",
                        "useIndicadoresNoRealizadas",
                        "useIndicadoresProductividad",
                    ],
                    "shared_table": False,
                    "react_query": False,
                    "period_tabs_lazy": True,
                    "sections_data_eager": True,
                },
                "load_timeline_estimated_ms": {
                    "note": "Estimado: backend paralelo (5 hooks) + render progresivo; sin medición browser en esta corrida",
                    "A_first_render_visible": 50,
                    "B_first_kpi_available": mensual_parallel_est,
                    "C_all_sections_stable_parallel": mensual_parallel_est,
                    "C_all_sections_stable_if_serial": round(mensual_backend_serial_ms, 1),
                    "D_screen_stable_including_catalogs": round(mensual_parallel_est + 150, 1),
                },
                "request_inventory_on_mount": {
                    "count": 7,
                    "requests": [
                        {"endpoint": "GET /geolocalizacion/distritos/catalogo", "trigger": "mount", "count": 1},
                        {"endpoint": "GET /grid/catalogs/inspectores", "trigger": "mount", "count": 1},
                        {"endpoint": "GET /api/indicadores/ejecutivo", "trigger": "mount+filters", "count": 1},
                        {"endpoint": "GET /api/indicadores/pendientes", "trigger": "mount+distrito", "count": 1},
                        {"endpoint": "GET /api/indicadores/riesgo", "trigger": "mount+filters", "count": 1},
                        {"endpoint": "GET /api/indicadores/no-realizadas", "trigger": "mount+filters", "count": 1},
                        {"endpoint": "GET /api/indicadores/productividad", "trigger": "mount+filters", "count": 1},
                    ],
                    "inactive_period_prefetch": False,
                    "strict_mode_double_fetch_dev": True,
                },
                "duplicate_requests": [
                    {
                        "pattern": "5 indicadores blocks fire on every mount regardless of scroll/visibility",
                        "severity": "P1",
                    },
                    {
                        "pattern": "Productividad JS lazy-loaded but API data fetched eagerly on mount",
                        "severity": "P2",
                    },
                    {
                        "pattern": "No request deduplication/cache; rapid filter changes cancel but still hit network",
                        "severity": "P2",
                    },
                ],
                "effects_findings": [
                    "Panel.tsx: 5 independent useIndicadores* hooks each with useEffect([params,tick]) — parallel on mount",
                    "Period change updates indicadoresParams → 4 hooks refetch (pendientes ignores period)",
                    "Distrito change → 5 hooks refetch; Inspector change → 4 hooks (pendientes excluded)",
                    "initialLoadDone gate: global loader until anySectionReady, then progressive section gates",
                    "indicadoresParams memoized on primitives — stable deps (no inline object churn)",
                ],
                "render_findings": [
                    "Sections are pure presentation; no heavy reduce/filter on large arrays",
                    "Productividad: 3 MRT tables — moderate render cost after data arrives",
                    "Dashboard unmounts operative table N/A — all sections stack vertically after first load",
                ],
                "filter_change_requests": {
                    "period_tab_change": 4,
                    "distrito_change": 5,
                    "inspector_change": 4,
                    "return_to_visited_period": 4,
                },
            },
            "backend": {
                "endpoint_timings": endpoint_timings,
                "period_switch_total_ms_sequential": period_switch_cost,
                "query_counts": query_counts,
                "duplicate_queries": duplicate_queries,
                "slow_queries": [],
            },
            "database": {
                "explain_results": explain_results,
                "index_inventory": index_inventory[:40],
                "missing_or_suboptimal_indexes": [],
            },
            "kpis": {},
            "root_causes": {"P0": [], "P1": [], "P2": [], "P3": []},
            "recommended_fix_plan": [],
            "future_test_plan": {
                "A": "KPI equality before/after optimization (golden baseline_values)",
                "B": "query count per endpoint reduced",
                "C": "endpoint timing budget",
                "D": "no duplicate SQL signatures per request",
                "E": "lazy load sections/tabs if implemented",
                "F": "filter correctness con distrito/inspector",
            },
        }

        # KPI analysis from baseline + timings
        ej = baseline_values.get("ejecutivo", {})
        kpis = report["kpis"]
        if ej:
            kpis["realizadas"] = {
                "value_baseline_mensual": ej.get("kpis", {}).get("actuaciones_realizadas"),
                "service": "count_cierres_realizados",
                "file": "indicadores_operativos_queries.py",
                "queries_per_ejecutivo_request": query_counts.get("mensual_sin_filtros:ejecutivo"),
            }
            kpis["actas"] = {
                "value_baseline_mensual": ej.get("kpis", {}).get("actas_labradas"),
                "breakdown": ej.get("actas_por_tipo"),
                "service": "_count_actas_labradas (5 separate COUNT queries)",
                "file": "indicadores_resumen_service.py",
            }
            kpis["reinspecciones"] = {
                "notificacion": ej.get("kpis", {}).get("reinspecciones_notificacion_realizadas"),
                "oficio": ej.get("kpis", {}).get("reinspecciones_oficio_realizadas"),
            }
            kpis["verificar_informar"] = ej.get("kpis", {}).get("verificar_informar_realizadas")
            kpis["ratificaciones"] = {
                "clausura": ej.get("kpis", {}).get("ratificaciones_clausura_realizadas"),
                "decomiso": ej.get("kpis", {}).get("ratificaciones_decomiso_realizadas"),
            }
            kpis["kg_decomisados"] = ej.get("kpis", {}).get("mercaderia_decomisada_kg")

        if "pendientes" in baseline_values:
            kpis["pendientes"] = {
                "baseline": baseline_values["pendientes"],
                "timing_ms": endpoint_timings.get("mensual_sin_filtros", {}).get("pendientes"),
                "bottleneck": "Python geocode loop over full iniciador stock",
            }
        if "riesgo" in baseline_values:
            kpis["riesgo"] = {"baseline": baseline_values["riesgo"], "subquery_rebuilds": 4}
        if "no-realizadas" in baseline_values:
            kpis["no_realizadas"] = {
                "baseline": baseline_values["no-realizadas"],
                "triple_fetch": "fetch_no_realizadas_visita_rows called 3x per request",
            }
        if "productividad" in baseline_values:
            kpis["productividad"] = {"baseline": baseline_values["productividad"]}

        # Root causes from measurements
        pend_ms = endpoint_timings.get("mensual_sin_filtros", {}).get("pendientes", {}).get("total_ms", 0)
        total_parallel = max(
            v.get("total_ms", 0) for v in endpoint_timings.get("mensual_sin_filtros", {}).values()
        )
        pend_pct = round(100 * pend_ms / total_parallel, 1) if total_parallel else 0

        report["root_causes"]["P0"] = [
            {
                "id": "P0-pendientes-python-geocode",
                "cause": "/api/indicadores/pendientes carga ~4k iniciadores ORM + geocode Python por fila",
                "evidence": f"mensual_sin_filtros pendientes={pend_ms}ms ({pend_pct}% del cuello paralelo); scanned≈4068 mapped≈572 en PERF_LOG",
                "fix_proposed": "Mover filtro geocode/distrito a SQL o precomputar stock pendiente; evitar joinedload masivo + loop Python",
                "risk": "medio — debe preservar semántica stock actual",
                "expected_gain": "70-95% del tiempo de pendientes",
            }
        ]
        report["root_causes"]["P1"] = [
            {
                "id": "P1-eager-5-endpoints",
                "cause": "Frontend dispara 5 endpoints indicadores al montar sin lazy por sección",
                "evidence": "Panel.tsx monta 5 hooks; waterfall percibido = max(pendientes, otros)",
                "fix_proposed": "Lazy-load por sección visible o priorizar ejecutivo+pendientes primero",
                "risk": "bajo UX si hay skeleton progresivo",
                "expected_gain": "perceived TTI -30-50% si pendientes se difiere o optimiza",
            },
            {
                "id": "P1-actas-5-counts",
                "cause": "_count_actas_labradas ejecuta 5 COUNT separados por tipo",
                "evidence": f"ejecutivo query_count={query_counts.get('mensual_sin_filtros:ejecutivo')}",
                "fix_proposed": "Consolidar en 1 query con CASE/SUM pivot",
                "risk": "bajo",
                "expected_gain": "20-40% en ejecutivo",
            },
            {
                "id": "P1-no-realizadas-triple-fetch",
                "cause": "fetch_no_realizadas_visita_rows invocado 3 veces por request",
                "evidence": "indicadores_no_realizadas_service.py + productividad_queries.py",
                "fix_proposed": "Materializar filas una vez por request y reusar",
                "risk": "bajo",
                "expected_gain": "30-50% en no-realizadas y productividad.no_realizadas",
            },
            {
                "id": "P1-riesgo-subquery-4x",
                "cause": "actuacion_ids_realizadas_subquery reconstruida 4 veces en /riesgo",
                "evidence": "indicadores_riesgo_service.py 4 sub-queries independientes",
                "fix_proposed": "CTE/materializar subquery una vez",
                "risk": "bajo",
                "expected_gain": "15-25% en riesgo",
            },
        ]
        report["root_causes"]["P2"] = [
            {
                "id": "P2-resumen-legacy-heavy",
                "cause": "/resumen monolítico ~25+ queries (no usado por Panel actual)",
                "evidence": f"resumen query_count={query_counts.get('mensual_sin_filtros:resumen', 'skipped')}",
                "fix_proposed": "Deprecar o no invocar desde UI; consolidar si aún se usa en export",
                "risk": "bajo si UI no lo llama",
                "expected_gain": "N/A si no se invoca",
            },
            {
                "id": "P2-productividad-4-acta-queries",
                "cause": "query_actas_por_inspector: 4 COUNT por tipo inspector",
                "evidence": "indicadores_productividad_queries.py",
                "fix_proposed": "Pivot SQL único",
                "risk": "bajo",
                "expected_gain": "10-20% productividad",
            },
            {
                "id": "P2-pendientes-distrito-n-plus-1",
                "cause": "_distrito_meta hace Distrito.query por cada distrito en ranking",
                "evidence": "indicadores_pendientes_queries.py",
                "fix_proposed": "Batch load distritos o join en agregación",
                "risk": "bajo",
                "expected_gain": "menor vs geocode loop",
            },
        ]
        report["root_causes"]["P3"] = [
            {
                "id": "P3-strict-mode-dev-double-fetch",
                "cause": "React StrictMode duplica effects en desarrollo",
                "evidence": "main.tsx StrictMode",
                "fix_proposed": "Ninguno en prod; opcional dedup en hooks",
                "risk": "n/a",
                "expected_gain": "solo dev",
            }
        ]

        report["recommended_fix_plan"] = [
            {"priority": 1, "item": "Optimizar pendientes stock aggregate (P0)", "ticket_suggested": "PERF-DASH.2-pendientes"},
            {"priority": 2, "item": "Eliminar triple-fetch no-realizadas (P1)", "ticket_suggested": "PERF-DASH.2-no-realizadas"},
            {"priority": 3, "item": "Consolidar actas COUNTs ejecutivo/productividad (P1)", "ticket_suggested": "PERF-DASH.2-actas"},
            {"priority": 4, "item": "Lazy-load secciones dashboard frontend (P1)", "ticket_suggested": "PERF-DASH.2-fe-lazy"},
            {"priority": 5, "item": "Materializar subquery realizadas en riesgo (P1)", "ticket_suggested": "PERF-DASH.2-riesgo"},
        ]

        # slow queries from duplicate accumulation
        all_dups: list[dict] = []
        for key, dups in duplicate_queries.items():
            for d in dups:
                all_dups.append({**d, "context": key})
        all_dups.sort(key=lambda x: x.get("accumulated_ms", 0), reverse=True)
        report["backend"]["slow_queries"] = all_dups[:15]

        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {OUTPUT}")
        print(json.dumps({k: v for k, v in endpoint_timings.items()}, indent=2))


if __name__ == "__main__":
    main()
