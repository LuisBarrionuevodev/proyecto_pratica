"""
PR5 — Diagnóstico nomenclatura pendiente sobre domicilios reales.

Solo lectura por defecto. Opcionalmente append de alias sugeridos al CSV.

Uso:
    cd Backend
    python -m app.scripts.diagnosticar_nomenclatura_pendiente
    python -m app.scripts.diagnosticar_nomenclatura_pendiente --limit 300
    python -m app.scripts.diagnosticar_nomenclatura_pendiente --apply-aliases
    python -m app.scripts.diagnosticar_nomenclatura_pendiente --apply-aliases --min-count 3
"""

from __future__ import annotations

import argparse
import json
import sys

from app import create_app
from app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_pendiente_diagnosis_service import (
    append_suggested_aliases_to_csv,
    diagnose_pendiente_nomenclatura,
)


def _print_section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _print_report(report: dict) -> None:
    _print_section("Resumen DB")
    print(f"Domicilios nomenclatura pendiente (total): {report['domicilios_pendientes_total']}")
    for status, n in sorted((report.get("status_breakdown_db") or {}).items()):
        print(f"  {status}: {n}")

    _print_section("Muestra analizada (top frecuencias)")
    print(f"Grupos distintos de calle: {report['unique_calle_groups_analyzed']}")
    print(f"Domicilios en esos grupos: {report['domicilios_in_top_groups']}")

    match = report.get("match_on_unique_texts") or {}
    print(
        f"Match sobre textos unicos -> OK={match.get('ok')} "
        f"REVIEW={match.get('review')} NO_MATCH={match.get('no_match')} "
        f"tasa_OK={match.get('success_rate')}"
    )

    sim = report.get("simulation") or {}
    _print_section("Simulación rematch (sin persistir)")
    print(f"Pasarían a OK (domicilios en muestra): {sim.get('would_become_ok_domicilios')}")
    print(f"Tasa OK simulada en muestra: {sim.get('simulated_ok_rate')}")
    print("Estado almacenado en muestra:", sim.get("stored_status_breakdown"))
    print("Estado simulado en muestra:", sim.get("simulated_status_breakdown"))

    _print_section("Top NO_MATCH (texto -> count)")
    for row in (sim.get("details") or [])[:15]:
        if row.get("simulated_status") != "NO_MATCH":
            continue
        print(f"  {row.get('count'):>4}x  {row.get('text')}")

    _print_section("Top REVIEW (texto -> count -> candidato)")
    for row in (sim.get("details") or [])[:20]:
        if row.get("simulated_status") != "REVIEW":
            continue
        cand = row.get("top_candidate") or {}
        print(
            f"  {row.get('count'):>4}x  {row.get('text')}  ->  "
            f"{cand.get('display')} (score={cand.get('score')})"
        )

    suggestions = report.get("suggested_aliases") or []
    _print_section(f"Alias sugeridos ({len(suggestions)})")
    for s in suggestions[:25]:
        print(
            f"  {s.get('count'):>4}x  {s.get('alias')!r}  ->  {s.get('nombre_canonico')}  "
            f"(score={s.get('score')})"
        )


def main(argv: list[str] | None = None) -> int:
    """
    Punto de entrada CLI.

    Parámetros:
        argv: argumentos (sin prog); None usa sys.argv.

    Retorno:
        Código de salida 0 si OK.
    """
    parser = argparse.ArgumentParser(description="Diagnóstico nomenclatura pendiente (PR5)")
    parser.add_argument("--limit", type=int, default=500, help="Top grupos de calle a analizar")
    parser.add_argument(
        "--min-count",
        type=int,
        default=2,
        help="Frecuencia mínima para sugerir alias",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.78,
        help="Score mínimo del candidato para sugerir alias",
    )
    parser.add_argument(
        "--apply-aliases",
        action="store_true",
        help="Append alias sugeridos a calle_aliases.csv (nuevos solamente)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime reporte completo en JSON",
    )
    args = parser.parse_args(argv)

    app = create_app()
    with app.app_context():
        report = diagnose_pendiente_nomenclatura(limit=args.limit)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        else:
            _print_report(report)

        if args.apply_aliases:
            from app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_pendiente_diagnosis_service import (
                simulate_rematch_for_samples,
                suggest_aliases_from_simulation,
                fetch_pendiente_calle_frecuencias,
            )

            samples = fetch_pendiente_calle_frecuencias(limit=args.limit)
            simulation = simulate_rematch_for_samples(samples)
            suggestions = suggest_aliases_from_simulation(
                simulation,
                min_count=args.min_count,
                min_score=args.min_score,
            )
            result = append_suggested_aliases_to_csv(suggestions, dry_run=False)
            _print_section("Alias aplicados al CSV")
            print(f"Agregados: {result['added']}")
            print(f"Omitidos (ya existían): {result['skipped_existing']}")
            for row in result.get("rows") or []:
                print(f"  + {row['alias']!r} -> {row['nombre_canonico']}")

            report2 = diagnose_pendiente_nomenclatura(limit=args.limit)
            if not args.json:
                _print_section("Re-diagnóstico post-alias")
                match = report2.get("match_on_unique_texts") or {}
                print(
                    f"OK={match.get('ok')} REVIEW={match.get('review')} "
                    f"NO_MATCH={match.get('no_match')} tasa_OK={match.get('success_rate')}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
