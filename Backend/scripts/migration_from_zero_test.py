#!/usr/bin/env python
"""
DEPLOY-PILOT.1 — Prueba de migración Alembic desde base vacía.

Uso:
  cd Backend
  python scripts/migration_from_zero_test.py

Usa TEST_DATABASE_URL (debe ser digitaliza_test u otra base *test* dedicada).
NO ejecuta contra digitaliza_sandbox ni bases productivas.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from flask_migrate import upgrade
from sqlalchemy import inspect, text

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from alembic.config import Config
from alembic.script import ScriptDirectory

from app import create_app
from app.database import db
from app.security.test_database import require_test_database_url, validate_test_database_url


def _alembic_head() -> list[str]:
    cfg = Config()
    cfg.set_main_option("script_location", os.path.join(BACKEND_ROOT, "migrations"))
    script = ScriptDirectory.from_config(cfg)
    return list(script.get_heads())


def main() -> int:
    load_dotenv()
    test_url = require_test_database_url()
    dev_uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    validate_test_database_url(test_url, dev_uri=dev_uri)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": test_url,
            "JWT_SECRET_KEY": "migration-from-zero-test-jwt-secret-32b",
        }
    )

    with app.app_context():
        engine = db.engine
        insp = inspect(engine)
        existing_tables = set(insp.get_table_names())
        if existing_tables - {"alembic_version"}:
            print(
                "ADVERTENCIA: la base de tests no está vacía; se ejecutará upgrade idempotente.",
                file=sys.stderr,
            )

        upgrade()

        with engine.connect() as conn:
            current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            counter = conn.execute(
                text("SELECT next_value FROM orden_trabajo_contador ORDER BY id ASC LIMIT 1")
            ).scalar()

        heads = _alembic_head()
        tables_after = set(inspect(engine).get_table_names())

        print(f"DATABASE: {test_url}")
        print(f"ALEMBIC_CURRENT: {current}")
        print(f"ALEMBIC_HEAD: {', '.join(heads)}")
        print(f"TABLE_COUNT: {len(tables_after)}")

        if current not in heads:
            print("FAIL: revisión actual no coincide con HEAD.", file=sys.stderr)
            return 1

        required_tables = {
            "users",
            "orden_trabajo",
            "orden_trabajo_contador",
            "distrito",
            "actuaciones",
            "ruta_trabajo",
            "ruta_item",
        }
        missing = sorted(required_tables - tables_after)
        if missing:
            print(f"FAIL: tablas requeridas ausentes: {missing}", file=sys.stderr)
            return 1
        print(f"OT_COUNTER_INITIAL: {counter}")
        print("PASS: migration from zero / upgrade to HEAD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
