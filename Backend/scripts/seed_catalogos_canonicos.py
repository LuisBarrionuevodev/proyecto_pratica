#!/usr/bin/env python
"""
Orquestador de catálogos canónicos Digitaliza (CATALOGOS-PREDEPLOY.3).

Uso:
  cd Backend
  python scripts/seed_catalogos_canonicos.py --dry-run
  python scripts/seed_catalogos_canonicos.py

Por defecto usa SQLALCHEMY_DATABASE_URI del .env.
"""

from __future__ import annotations

import argparse
import os
import sys
from urllib.parse import unquote

from dotenv import load_dotenv

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.database import db
from app.domains.catalogos.canonical.manifest import CATALOG_VERSION, EXPECTED_COUNTS
from app.domains.catalogos.seeds.seed_canonical_service import (
    canonical_names_contain_qa,
    run_canonical_catalog_seed,
)
from app.domains.catalogos.seeds.validate_canonical import validate_canonical_catalogs


def _database_name(uri: str) -> str:
    return unquote(uri.rsplit("/", 1)[-1].split("?", 1)[0])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed de catálogos canónicos Digitaliza.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula el seed sin escribir en la base.",
    )
    parser.add_argument(
        "--database-uri",
        default=None,
        help="URI MySQL destino (default: SQLALCHEMY_DATABASE_URI).",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="No ejecutar validación post-seed.",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv(os.path.join(BACKEND_ROOT, ".env"))
    args = parse_args()
    uri = (args.database_uri or os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri:
        print("SQLALCHEMY_DATABASE_URI no configurada.", file=sys.stderr)
        return 1

    db_name = _database_name(uri)
    print(f"DATABASE DESTINO: {db_name}")
    print(f"CATALOG_VERSION: {CATALOG_VERSION}")
    print(f"MODO: {'DRY-RUN (sin writes)' if args.dry_run else 'WRITE'}")

    qa = canonical_names_contain_qa()
    if qa:
        print("ADVERTENCIA: patrones QA en fuentes canónicas:", qa, file=sys.stderr)
        return 1

    dev_uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    is_test_db = "test" in db_name.lower()
    if is_test_db:
        os.environ["TEST_DATABASE_URL"] = uri
        if dev_uri and dev_uri != uri and "test" not in _database_name(dev_uri).lower():
            os.environ.setdefault("PYTEST_ORIGINAL_DEV_DATABASE_URI", dev_uri)
    os.environ["SQLALCHEMY_DATABASE_URI"] = uri
    if is_test_db:
        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": uri,
                "JWT_SECRET_KEY": "seed-catalogos-canonicos-jwt-secret-32b",
            }
        )
    else:
        app = create_app(
            {
                "JWT_SECRET_KEY": "seed-catalogos-canonicos-jwt-secret-32b",
            }
        )

    with app.app_context():
        result = run_canonical_catalog_seed(db.session, dry_run=args.dry_run)
        print("\nResultado por catálogo:")
        for catalog, metrics in result.catalogs.items():
            print(
                f"  {catalog}: created={metrics['created']} "
                f"updated={metrics['updated']} skipped={metrics['skipped']}"
            )
        if result.conflicts:
            print("Conflictos:", result.conflicts)

        if not args.dry_run and not args.skip_validate:
            validate_canonical_catalogs(db.session)
            print("\nValidación: todos los canónicos presentes.")
            print("Conteos esperados (manifest):", EXPECTED_COUNTS)

    print("\nConfirmación: dry-run no escribió." if args.dry_run else "Seed completado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
