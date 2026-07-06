"""
PR5/PR5b — Diagnóstico nomenclatura pendiente sobre domicilios reales.

Fuente oficial: calle_catalogo (DB). CSV alias solo variantes validadas.

Uso:
    cd Backend
    python -m app.scripts.diagnosticar_nomenclatura_pendiente
    python -m app.scripts.diagnosticar_nomenclatura_pendiente --limit 300
    python -m app.scripts.diagnosticar_nomenclatura_pendiente --apply-aliases
    python -m app.scripts.diagnosticar_nomenclatura_pendiente --json > nomenclatura_reporte.json
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
    print(f"Fuente oficial: {report.get('fuente_oficial')}")
    print(f"Rol CSV alias: {report.get('alias_csv_rol')}")
    print(f"Domicilios nomenclatura pendiente (total): {report['domicilios_pendientes_total']}")
    for status, n in sorted((report.get("status_breakdown_db") or {}).items()):
        print(f"  {status}: {n}")

    alias_audit = report.get("alias_audit") or {}
    _print_section("Auditoria alias CSV vs calle_catalogo")
    print(f"Validos: {alias_audit.get('valid_count', 0)}")
    print(f"Invalidos: {alias_audit.get('invalid_count', 0)}")
    for row in (alias_audit.get("invalid") or [])[:10]:
        print(
            f"  INVALIDO  {row.get('alias')!r} -> {row.get('nombre_canonico')}  "
            f"({row.get('reason')})"
        )
    for row in (alias_audit.get("valid") or [])[:10]:
        print(f"  OK        {row.get('alias')!r} -> {row.get('nombre_canonico')}")

    split = report.get("origin_split") or {}
    _print_section("Separacion real vs sintetico (tests)")
    print(f"Grupos reales: {split.get('real_groups')}  domicilios: {split.get('real_domicilios')}")
    print(
        f"Grupos sinteticos: {split.get('synthetic_groups')}  "
        f"domicilios: {split.get('synthetic_domicilios')}"
    )

    match_real = report.get("match_on_real_texts") or {}
    _print_section("Match calles REALES vs calle_catalogo")
    print(
        f"Textos unicos reales -> OK={match_real.get('ok')} "
        f"REVIEW={match_real.get('review')} NO_MATCH={match_real.get('no_match')} "
        f"tasa_OK={match_real.get('success_rate')}"
    )

    sim = report.get("simulation") or {}
    _print_section("Simulacion rematch REALES (sin persistir)")
    print(f"Pasarían a OK (solo reales): {split.get('real_would_become_ok')}")
    print(f"Tasa OK simulada reales: {split.get('real_simulated_ok_rate')}")
    print("Estado simulado reales:", split.get("real_simulated_status_breakdown"))

    _print_section("Top NO_MATCH REALES (catalogo o alias)")
    for row in (report.get("top_real_no_match") or [])[:15]:
        cand = row.get("top_candidate") or {}
        cand_txt = (
            f" -> {cand.get('display')} (score={cand.get('score')})"
            if cand
            else ""
        )
        print(f"  {row.get('count'):>4}x  {row.get('text')}{cand_txt}")

    _print_section("Top NO_MATCH SINTETICOS (tests, ignorar)")
    for row in (sim.get("details") or [])[:15]:
        if row.get("simulated_status") != "NO_MATCH" or not row.get("is_synthetic"):
            continue
        print(f"  {row.get('count'):>4}x  {row.get('text')}")

    _print_section("Top REVIEW REALES")
    for row in (sim.get("details") or [])[:20]:
        if row.get("simulated_status") != "REVIEW" or row.get("is_synthetic"):
            continue
        cand = row.get("top_candidate") or {}
        print(
            f"  {row.get('count'):>4}x  {row.get('text')}  ->  "
            f"{cand.get('display')} (score={cand.get('score')})"
        )

    suggestions = report.get("suggested_aliases") or []
    _print_section(f"Alias sugeridos validos ({len(suggestions)})")
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
    parser = argparse.ArgumentParser(description="Diagnóstico nomenclatura pendiente (PR5b)")
    parser.add_argument("--limit", type=int, default=500, help="Top grupos de calle a analizar")
    parser.add_argument(
        "--min-count",
        type=int,
        default=2,
        help="Frecuencia minima para sugerir alias",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.78,
        help="Score minimo del candidato para sugerir alias",
    )
    parser.add_argument(
        "--apply-aliases",
        action="store_true",
        help="Append alias sugeridos a calle_aliases.csv (nuevos y validos)",
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
                fetch_pendiente_calle_frecuencias,
                simulate_rematch_for_samples,
                suggest_aliases_from_simulation,
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
            print(f"Omitidos (ya existian): {result['skipped_existing']}")
            print(f"Omitidos (canon invalido): {result['skipped_invalid_canon']}")
            for row in result.get("rows") or []:
                print(f"  + {row['alias']!r} -> {row['nombre_canonico']}")

            report2 = diagnose_pendiente_nomenclatura(limit=args.limit)
            if not args.json:
                _print_section("Re-diagnostico post-alias (reales)")
                match = report2.get("match_on_real_texts") or {}
                print(
                    f"OK={match.get('ok')} REVIEW={match.get('review')} "
                    f"NO_MATCH={match.get('no_match')} tasa_OK={match.get('success_rate')}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
