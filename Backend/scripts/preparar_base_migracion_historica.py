#!/usr/bin/env python
"""
Bootstrap local seguro: Alembic head + seed en ``digitaliza_migracion``.

V1.1-MIG-ACTAS.1B — verifica ``SELECT DATABASE()`` antes de escribir.
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

from alembic.config import Config
from alembic.script import ScriptDirectory
from flask_migrate import upgrade
from sqlalchemy import inspect, text

from app.database import db
from app.domains.catalogos.canonical.manifest import CATALOG_VERSION
from app.domains.catalogos.seeds.seed_canonical_service import (
    canonical_names_contain_qa,
    run_canonical_catalog_seed,
)
from app.domains.catalogos.seeds.validate_canonical import validate_canonical_catalogs
from app.domains.migracion_historica.historico_migracion_import_security import (
    ALLOWED_MIGRACION_DATABASE,
    HistoricoMigracionImportSecurityError,
    validate_migracion_import_database_uri,
)
from app.domains.migracion_historica.migracion_target_connection import (
    MigracionTargetConnectionError,
    create_migracion_flask_app,
    fetch_effective_database_name,
    verify_migracion_connection,
)

EXPECTED_HEAD_REVISION = "a2b3c4d5e6f8"
OPERATIONAL_TABLES = (
    "actuaciones",
    "orden_trabajo",
    "notificacion",
    "comprobacion",
    "migracion_historica_registro",
    "motivo",
    "rubro",
    "inspector",
    "alembic_version",
)


def _alembic_head_revision() -> str:
    migrations_dir = _BACKEND_ROOT / "migrations"
    cfg = Config()
    cfg.set_main_option("script_location", str(migrations_dir))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"Se esperaba un único head Alembic; encontrados: {heads}")
    return heads[0]


def main(argv: list[str] | None = None) -> int:
    """
    Prepara ``digitaliza_migracion``: migrate head, verificación y seed de catálogos.

    Returns:
        0 si todo OK; 2 en error de destino o conexión.
    """
    parser = argparse.ArgumentParser(description="Bootstrap digitaliza_migracion (local).")
    parser.add_argument("--database-uri", required=True, help="URI MySQL local digitaliza_migracion.")
    parser.add_argument("--skip-seed", action="store_true", help="Solo migraciones y verificación.")
    parser.add_argument("--dry-run-seed", action="store_true", help="Seed en modo simulación.")
    args = parser.parse_args(argv)

    try:
        target = validate_migracion_import_database_uri(args.database_uri.strip())
    except HistoricoMigracionImportSecurityError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    qa = canonical_names_contain_qa()
    if qa:
        print("Patrones QA en catálogos canónicos:", qa, file=sys.stderr)
        return 2

    app = create_migracion_flask_app(args.database_uri.strip())

    with app.app_context():
        try:
            verified = verify_migracion_connection(db.session, target)
        except MigracionTargetConnectionError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        upgrade()
        db.session.remove()

        efectiva = fetch_effective_database_name(db.session)
        if (efectiva or "").lower() != ALLOWED_MIGRACION_DATABASE:
            print("Tras upgrade: base efectiva no es digitaliza_migracion.", file=sys.stderr)
            return 2

        insp = inspect(db.engine)
        missing = [t for t in OPERATIONAL_TABLES if not insp.has_table(t)]
        if missing:
            print(f"Faltan tablas operativas: {', '.join(missing)}", file=sys.stderr)
            return 2

        revision = db.session.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        head = _alembic_head_revision()
        if revision != head:
            print(
                f"Revisión Alembic {revision} distinta del head esperado {head}.",
                file=sys.stderr,
            )
            return 2

        catalogos_ok = "SKIP"
        if not args.skip_seed:
            run_canonical_catalog_seed(db.session, dry_run=args.dry_run_seed)
            if not args.dry_run_seed:
                validate_canonical_catalogs(db.session)
            catalogos_ok = "OK" if not args.dry_run_seed else "DRY-RUN"

    print(f"Base efectiva: {verified.database_efectiva}")
    print(f"Host: {verified.target.host}")
    print(f"Alembic: {revision}")
    print("Tablas operativas: OK")
    print(f"Catálogos: {catalogos_ok}")
    print(f"CATALOG_VERSION: {CATALOG_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
