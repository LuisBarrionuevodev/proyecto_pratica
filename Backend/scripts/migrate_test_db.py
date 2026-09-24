#!/usr/bin/env python
"""
Aplica Alembic upgrade head contra TEST_DATABASE_URL (no toca Development).

Uso:
  cd Backend
  python scripts/migrate_test_db.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from flask_migrate import upgrade

# Raíz Backend en sys.path
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.security.test_database import require_test_database_url, validate_test_database_url


def main() -> int:
    load_dotenv()
    test_url = require_test_database_url()
    dev_uri = (os.getenv("SQLALCHEMY_DATABASE_URI") or "").strip()
    validate_test_database_url(test_url, dev_uri=dev_uri)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": test_url,
            "JWT_SECRET_KEY": "migrate-test-db-jwt-secret-32bytes-min",

        }
    )
    with app.app_context():
        upgrade()
    print(f"Migraciones aplicadas en: {test_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
