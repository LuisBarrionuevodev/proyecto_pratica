"""
OPER-ANALYTICS.2 — Diagnóstico golden dataset contra DB real (READ ONLY).

Uso:
    cd Backend
    set PYTHONPATH=.
    python -m app.scripts.diagnostico_oper_analytics_golden
    python -m app.scripts.diagnostico_oper_analytics_golden --desde 2026-06-01 --hasta 2026-06-30
    python -m app.scripts.diagnostico_oper_analytics_golden --distrito-id 3 --inspector-id 5
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

from app import create_app
from app.domains.indicadores.diagnostics.oper_analytics_golden import (
    compare_dashboard,
    compare_mapa,
    compute_baseline_metrics,
    fetch_golden_dataset,
    format_baseline_report,
)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _default_range() -> tuple[date, date]:
    hoy = date.today()
    desde = hoy.replace(day=1)
    if hoy.month == 12:
        hasta = date(hoy.year, 12, 31)
    else:
        hasta = date(hoy.year, hoy.month + 1, 1) - timedelta(days=1)
    return desde, hasta


def main() -> None:
    parser = argparse.ArgumentParser(description="Golden dataset operativo (solo lectura)")
    parser.add_argument("--desde", type=_parse_date, help="Fecha inicio ISO (RutaTrabajo.fecha)")
    parser.add_argument("--hasta", type=_parse_date, help="Fecha fin ISO")
    parser.add_argument("--distrito-id", type=int, default=None)
    parser.add_argument("--inspector-id", type=int, default=None)
    parser.add_argument("--json", action="store_true", help="Salida JSON en lugar de texto")
    args = parser.parse_args()

    desde, hasta = args.desde, args.hasta
    if desde is None or hasta is None:
        desde, hasta = _default_range()

    app = create_app()
    with app.app_context():
        rows = fetch_golden_dataset(
            desde,
            hasta,
            distrito_id=args.distrito_id,
            inspector_id=args.inspector_id,
        )
        metrics = compute_baseline_metrics(rows)
        dashboard = compare_dashboard(
            desde,
            hasta,
            rows,
            distrito_id=args.distrito_id,
            inspector_id=args.inspector_id,
        )
        mapa = compare_mapa(
            desde,
            hasta,
            rows,
            distrito_id=args.distrito_id,
            inspector_id=args.inspector_id,
        )

        if args.json:
            payload = {
                "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
                "filtros": {
                    "distrito_id": args.distrito_id,
                    "inspector_id": args.inspector_id,
                },
                "metrics": {
                    "total_intentos": metrics.total_intentos,
                    "total_realizados": metrics.total_realizados,
                    "total_no_realizados": metrics.total_no_realizados,
                    "con_geocode_ok": metrics.con_geocode_ok,
                    "sin_geocode_ok": metrics.sin_geocode_ok,
                    "por_origen": metrics.por_origen,
                    "por_subtipo_oficio": metrics.por_subtipo_oficio,
                    "actas": {
                        "inspeccion": metrics.actas_inspeccion,
                        "notificacion": metrics.actas_notificacion,
                        "comprobacion": metrics.actas_comprobacion,
                        "clausura": metrics.actas_clausura,
                        "decomiso": metrics.actas_decomiso,
                        "total": metrics.total_actas_labradas,
                    },
                    "kg_realizados": metrics.kg_realizados,
                    "kg_no_realizados": metrics.kg_no_realizados,
                    "verificar_informar": metrics.verificar_informar,
                    "no_realizados_dibujables": metrics.no_realizados_dibujables,
                    "sin_geo": metrics.sin_geo[:100],
                },
                "dashboard": [
                    {
                        "kpi": r.kpi,
                        "baseline": r.baseline,
                        "endpoint": r.endpoint,
                        "diferencia": r.diferencia,
                        "ids_responsables": r.ids_responsables[:50],
                    }
                    for r in dashboard
                ],
                "mapa": {
                    "baseline_ids": mapa.baseline_ids[:200],
                    "mapa_ids": mapa.mapa_ids[:200],
                    "interseccion": mapa.interseccion[:200],
                    "solo_baseline": mapa.solo_baseline[:100],
                    "solo_mapa": mapa.solo_mapa[:100],
                    "explicacion_fecha_ids": mapa.explicacion_fecha_ids[:100],
                },
                "dataset_muestra": [r.to_dict() for r in rows[:50]],
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(
                format_baseline_report(
                    metrics,
                    dashboard=dashboard,
                    mapa=mapa,
                )
            )
            print("")
            print(f"Periodo: {desde.isoformat()} - {hasta.isoformat()}")
            if args.distrito_id:
                print(f"Distrito filtro: {args.distrito_id}")
            if args.inspector_id:
                print(f"Inspector filtro: {args.inspector_id}")


if __name__ == "__main__":
    main()
