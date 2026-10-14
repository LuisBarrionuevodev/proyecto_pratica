#!/usr/bin/env python
"""
CLI read-only: inventario de actas históricas EpiCollect (dry-run).

No importa Flask ni SQLAlchemy. No imprime PII ni URLs en consola.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

# Permite ejecutar desde Backend/ sin instalar el paquete.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.domains.migracion_historica.epicollect_actas_inventario import (  # noqa: E402
    assert_output_outside_repo,
    inventariar_csv,
    resolve_repo_root,
    write_inventario_outputs,
)


def _parse_cutoff(raw: str) -> date:
    try:
        return date.fromisoformat(raw.strip())
    except ValueError as exc:
        raise SystemExit(f"Fecha de corte inválida (use YYYY-MM-DD): {raw}") from exc


def main(argv: list[str] | None = None) -> int:
    """
    Punto de entrada del inventario histórico EpiCollect.

    Args:
        argv: argumentos CLI (por defecto sys.argv[1:]).

    Returns:
        0 si el inventario se generó correctamente.

    Raises:
        SystemExit: argumentos inválidos o salida dentro del repositorio.
    """
    parser = argparse.ArgumentParser(
        description="Inventario read-only de actas históricas EpiCollect (sin escritura en DB)."
    )
    parser.add_argument("--input", required=True, type=Path, help="Ruta al CSV exportado (fuera de Git).")
    parser.add_argument(
        "--cutoff-date",
        default="2026-10-01",
        help="Fecha de corte (excluye filas con fecha >= corte). Formato YYYY-MM-DD.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directorio de salida (debe estar fuera del repositorio).",
    )
    parser.add_argument(
        "--legacy-inventory",
        type=Path,
        default=None,
        help="CSV inventario MySQL histórico (opcional, fuera de Git).",
    )
    args = parser.parse_args(argv)

    input_path: Path = args.input
    output_dir: Path = args.output
    cutoff = _parse_cutoff(args.cutoff_date)

    if not input_path.is_file():
        raise SystemExit("No se encontró el archivo --input.")
    if args.legacy_inventory is not None and not args.legacy_inventory.is_file():
        raise SystemExit("No se encontró el archivo --legacy-inventory.")

    repo_root = resolve_repo_root(_BACKEND_ROOT)
    assert_output_outside_repo(output_dir, repo_root)

    result = inventariar_csv(input_path, cutoff, legacy_inventory=args.legacy_inventory)
    write_inventario_outputs(result, output_dir)

    msg = (
        f"Inventario generado. filas={result.total_filas_leidas} "
        f"historicas={result.total_anterior_corte} "
        f"epi_sha256={result.source_sha256[:12]}…"
    )
    if result.legacy_inventory_sha256:
        msg += f" legacy_sha256={result.legacy_inventory_sha256[:12]}…"
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
