from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

from app import create_app


app = create_app()


def _run_flask_db(args: list[str], cwd: Path) -> None:
    env = os.environ.copy()
    env.setdefault("FLASK_APP", "run.py")
    subprocess.run(
        [sys.executable, "-m", "flask", "db", *args],
        cwd=str(cwd),
        env=env,
        check=True,
    )


def _setup_command(csv_path: str, message: str, no_migrate: bool) -> None:
    project_root = Path(__file__).resolve().parent
    migrations_dir = project_root / "migrations"
    csv_file = Path(csv_path)
    if not csv_file.is_absolute():
        csv_file = (project_root / csv_file).resolve()
    if not csv_file.exists():
        raise SystemExit(f"CSV no existe: {csv_file}")

    print("Setup: verificando migraciones...")
    if not migrations_dir.exists():
        print("Setup: ejecutando flask db init")
        _run_flask_db(["init"], project_root)
    else:
        print("Setup: migrations/ ya existe, se omite init")

    if not no_migrate:
        print(f"Setup: ejecutando flask db migrate -m {message!r}")
        _run_flask_db(["migrate", "-m", message], project_root)
    else:
        print("Setup: --no-migrate activo, se omite migrate")

    print("Setup: ejecutando flask db upgrade")
    _run_flask_db(["upgrade"], project_root)

    print("Setup: importando catalogo de calles")
    from app.domains.geolocalizacion.normalizacion_calles.pipelines.import_calle_catalogo import (
        importar_csv,
    )

    with app.app_context():
        created, updated, skipped = importar_csv(str(csv_file))
    print(f"Setup: import OK created={created} updated={updated} skipped={skipped}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    setup_parser = subparsers.add_parser("setup", help="Migraciones + upgrade + import CSV")
    setup_parser.add_argument("--csv", required=True, help="Ruta al CSV de calles")
    setup_parser.add_argument(
        "--message",
        default="auto migration",
        help="Mensaje para flask db migrate",
    )
    setup_parser.add_argument(
        "--no-migrate",
        action="store_true",
        help="Omitir flask db migrate",
    )
    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "setup":
        _setup_command(args.csv, args.message, args.no_migrate)
    else:
        app.run(debug=True)
