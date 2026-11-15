"""Corrige alembic_version local cuando apunta a una revisión inexistente."""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")
sys.path.insert(0, str(BACKEND_ROOT))

from app.security.deployment_config import resolve_sqlalchemy_database_uri

STAMP = "z1a2b3c4d5e6"


def main() -> int:
    uri = resolve_sqlalchemy_database_uri()
    eng = create_engine(uri)
    with eng.begin() as conn:
        before = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        conn.execute(text("UPDATE alembic_version SET version_num = :v"), {"v": STAMP})
        after = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    print(f"alembic_version: {before} -> {after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())