"""
REL-DISTRITO-BACKFILL.1 — Reparar domicilios geolocalizados sin distrito.

Uso:
    cd Backend
    python scripts/backfill_domicilios_distrito_geo_ok.py

    # Aplicar cambios (tras revisar dry-run):
    python scripts/backfill_domicilios_distrito_geo_ok.py --apply

    # Un domicilio puntual:
    python scripts/backfill_domicilios_distrito_geo_ok.py --apply --domicilio-id 13871

    # Límite y lotes:
    python scripts/backfill_domicilios_distrito_geo_ok.py --apply --limit 100 --batch-size 25
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.domains.geolocalizacion.geocode.services.distrito_backfill_service import (
    count_domicilios_geo_ok_sin_distrito,
    run_backfill_domicilios_geo_ok_sin_distrito,
)


def _print_summary(summary) -> None:
    data = summary.to_dict()
    print("=== REL-DISTRITO-BACKFILL.1 ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("\n--- Desglose por distrito ---")
    if summary.por_distrito:
        for label, count in sorted(summary.por_distrito.items()):
            print(f"  {label}: {count}")
    else:
        print("  (sin asignaciones)")
    print(f"  Sin match: {summary.no_match}")
    print(f"  Errores: {summary.errors}")
    print("\n--- Auditoría ---")
    print(f"  ANTES  geo OK + coords + distrito NULL: {summary.antes_geo_ok_sin_distrito}")
    print(f"  Resueltos: {summary.assigned}")
    print(f"  Sin match: {summary.no_match}")
    print(f"  Errores: {summary.errors}")
    print(f"  DESPUÉS restantes: {summary.despues_restantes}")
    if summary.error_details:
        print("\n--- Detalle errores (máx. 20) ---")
        for row in summary.error_details[:20]:
            print(row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill de distrito para domicilios con geocode OK y distrito_id NULL"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persistir cambios (default: dry-run sin commit)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecutar sin commit (equivale al modo por defecto)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Máximo de candidatos a procesar")
    parser.add_argument("--domicilio-id", type=int, default=None, help="Procesar un solo domicilio")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Tamaño de lote para commits en modo --apply (default: 50)",
    )
    args = parser.parse_args()

    apply = bool(args.apply) and not args.dry_run

    app = create_app()
    with app.app_context():
        antes_total = count_domicilios_geo_ok_sin_distrito(domicilio_id=args.domicilio_id)
        print(f"Candidatos detectados: {antes_total}")
        if antes_total == 0:
            print("No hay candidatos para procesar.")
            return

        summary = run_backfill_domicilios_geo_ok_sin_distrito(
            apply=apply,
            limit=args.limit,
            domicilio_id=args.domicilio_id,
            batch_size=args.batch_size,
        )
        _print_summary(summary)
        if not apply:
            print("\nDry-run: no se modificó la base. Usar --apply para persistir.")


if __name__ == "__main__":
    main()
