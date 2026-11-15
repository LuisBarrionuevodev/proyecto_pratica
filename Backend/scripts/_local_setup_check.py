"""One-off local env check (no secrets printed)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT))

from app.security.deployment_config import resolve_sqlalchemy_database_uri  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402


def main() -> int:
    uri = resolve_sqlalchemy_database_uri()
    if not uri or "USER:PASS" in uri:
        print("DATABASE_URL/SQLALCHEMY_DATABASE_URI: FALTA o placeholder")
        return 1
    print("DATABASE_URL/SQLALCHEMY_DATABASE_URI: OK")

    test_uri = (os.getenv("TEST_DATABASE_URL") or "").strip()
    if not test_uri:
        print("TEST_DATABASE_URL: FALTA")
        return 1
    print("TEST_DATABASE_URL: OK")

    eng = create_engine(uri)
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("MySQL (dev): conexion OK")

    test_eng = create_engine(test_uri)
    with test_eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("MySQL (test): conexion OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())