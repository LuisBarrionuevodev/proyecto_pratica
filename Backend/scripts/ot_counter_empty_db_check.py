#!/usr/bin/env python
"""DEPLOY-PILOT.2A — Verifica next_value=89862 tras upgrade en schema vacío."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from flask_migrate import upgrade
from sqlalchemy import create_engine, inspect, text

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.database import db

EXPECTED = 89862


def _drop_all_tables(engine) -> None:
    insp = inspect(engine)
    tables = insp.get_table_names()
    if not tables:
        return
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def main() -> int:
    load_dotenv(os.path.join(BACKEND_ROOT, ".env"))
    source = (os.getenv("TEST_DATABASE_URL") or "").strip()
    if not source:
        print("Falta TEST_DATABASE_URL", file=sys.stderr)
        return 1

    engine = create_engine(source)
    _drop_all_tables(engine)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": source,
            "JWT_SECRET_KEY": "empty-db-check-jwt-secret-32chars",
        }
    )

    with app.app_context():
        upgrade()
        row = db.session.execute(
            text("SELECT next_value FROM orden_trabajo_contador ORDER BY id ASC LIMIT 1")
        ).scalar()
        current = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        tables = len(inspect(db.engine).get_table_names())

    print(f"ALEMBIC: {current}")
    print(f"TABLE_COUNT: {tables}")
    print(f"OT_COUNTER_NEXT_VALUE: {row}")
    print(f"EXPECTED: {EXPECTED}")

    if int(row) != EXPECTED:
        print("FAIL: counter mismatch on empty schema", file=sys.stderr)
        return 2
    print("PASS: empty schema counter deterministic.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
