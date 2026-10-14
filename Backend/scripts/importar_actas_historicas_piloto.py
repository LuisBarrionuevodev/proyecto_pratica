#!/usr/bin/env python
"""
CLI piloto de importación histórica en digitaliza_migracion (V1.1-MIG-ACTAS.1A).

Por defecto dry-run. Apply requiere --apply --confirm-batch <batch-id>.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(_BACKEND_ROOT / ".env")

from app import create_app  # noqa: E402
from app.domains.migracion_historica.epicollect_actas_inventario import parse_inspection_date  # noqa: E402
from app.domains.migracion_historica.historico_migracion_import_security import (  # noqa: E402
    HistoricoMigracionImportSecurityError,
    validate_migracion_import_database_uri,
)
from app.domains.migracion_historica.historico_piloto_import_service import (  # noqa: E402
    run_pilot_import,
)


def main(argv: list[str] | None = None) -> int:
    """
    Ejecuta dry-run o apply del piloto de actas históricas.

    Returns:
        0 si finalizó; 2 en error de argumentos o seguridad.
    """
    parser = argparse.ArgumentParser(
        description="Piloto local de importación histórica (digitaliza_migracion)."
    )
    parser.add_argument("--database-uri", required=True, help="URI MySQL local digitaliza_migracion.")
    parser.add_argument("--epicollect-csv", required=True, type=Path)
    parser.add_argument("--sandbox-evidence-csv", required=True, type=Path)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cutoff-date", default="2026-10-01")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula sin escribir (predeterminado si no se usa --apply).",
    )
    parser.add_argument("--apply", action="store_true", default=False)
    parser.add_argument("--confirm-batch", default=None)
    args = parser.parse_args(argv)

    if args.apply and args.dry_run:
        print("No combine --apply con --dry-run.", file=sys.stderr)
        return 2
    dry_run = not args.apply

    cutoff, note = parse_inspection_date(args.cutoff_date)
    if cutoff is None:
        print(f"Fecha de corte inválida: {note}", file=sys.stderr)
        return 2

    try:
        target = validate_migracion_import_database_uri(args.database_uri.strip())
    except HistoricoMigracionImportSecurityError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    uri = args.database_uri.strip()
    os.environ["SQLALCHEMY_DATABASE_URI"] = uri
    app = create_app(
        {
            "JWT_SECRET_KEY": "piloto-import-historico-jwt-secret-32",
            "SQLALCHEMY_DATABASE_URI": uri,
        }
    )

    with app.app_context():
        try:
            result = run_pilot_import(
                output_dir=args.output,
                epicollect_csv=args.epicollect_csv,
                sandbox_evidence_csv=args.sandbox_evidence_csv,
                batch_id=args.batch_id,
                cutoff=cutoff,
                dry_run=dry_run,
                apply=args.apply,
                confirm_batch=args.confirm_batch,
                target=target,
                repo_root=_BACKEND_ROOT.parent,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    r = result.resumen
    print(
        "Piloto histórico.",
        f"modo={r.get('modo')}",
        f"candidatas={r.get('candidatas_evidencia_finalizada')}",
        f"aplicables={r.get('aplicables')}",
        f"insertadas={r.get('insertadas')}",
        f"revisar={r.get('revisar')}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
