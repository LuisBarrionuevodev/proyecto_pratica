#!/usr/bin/env python
"""
CLI read-only: export enriquecido de actuaciones desde digitaliza_sandbox local.

No imprime URI, credenciales ni filas con PII en consola.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(_BACKEND_ROOT / ".env")

from app.domains.migracion_historica.epicollect_actas_inventario import parse_inspection_date  # noqa: E402
from app.domains.migracion_historica.historico_actas_enriquecido_export import (  # noqa: E402
    export_actas_historicas_enriquecidas,
)
from app.domains.migracion_historica.historico_sandbox_odt_evidencia import (  # noqa: E402
    export_evidencia_sandbox_por_odt,
)


def main(argv: list[str] | None = None) -> int:
    """
    Exporta inventario enriquecido a un directorio fuera del repositorio.

    Returns:
        0 si el export finalizó correctamente.
    """
    parser = argparse.ArgumentParser(
        description="Export read-only de actuaciones históricas enriquecidas (digitaliza_sandbox local)."
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directorio de salida (fuera del repositorio).",
    )
    parser.add_argument(
        "--database-uri",
        default=None,
        help="URI opcional; debe pasar las mismas validaciones de sandbox local.",
    )
    parser.add_argument(
        "--epicollect-csv",
        default=None,
        type=Path,
        help="CSV EpiCollect congelado: modo evidencia sandbox filtrada por ODT/año.",
    )
    parser.add_argument(
        "--cutoff-date",
        default="2026-10-01",
        help="Fecha de corte (YYYY-MM-DD) para filas EpiCollect históricas.",
    )
    args = parser.parse_args(argv)

    if args.epicollect_csv is not None:
        cutoff, note = parse_inspection_date(args.cutoff_date)
        if cutoff is None:
            print(f"Fecha de corte inválida: {note}", file=sys.stderr)
            return 2
        result = export_evidencia_sandbox_por_odt(
            args.output,
            args.epicollect_csv,
            cutoff,
            database_uri=args.database_uri,
            repo_root=_BACKEND_ROOT.parent,
        )
        r = result.resumen
        print(
            "Evidencia sandbox por ODT generada.",
            f"finalizadas={r.get('evidencias_finalizadas', 0)}",
            f"ambiguas={r.get('coincidencias_ambiguas', 0)}",
            f"descartadas_sandbox={r.get('sandbox_descartadas_no_en_epicollect', 0)}",
        )
        return 0

    result = export_actas_historicas_enriquecidas(
        args.output,
        database_uri=args.database_uri,
        repo_root=_BACKEND_ROOT.parent,
    )
    print(
        "Export enriquecido generado.",
        f"filas={result.total_exportadas}",
        f"sha256={result.csv_sha256[:12]}…",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
