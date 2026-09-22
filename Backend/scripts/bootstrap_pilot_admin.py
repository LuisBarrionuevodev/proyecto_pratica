#!/usr/bin/env python
"""
Bootstrap de usuario ADMIN inicial para piloto cloud (ejecución única).

Uso:
  cd Backend
  set PILOT_ADMIN_USERNAME=admin
  set PILOT_ADMIN_EMAIL=admin@ejemplo.gob.ar
  set PILOT_ADMIN_PASSWORD=<secreto-fuerte>
  python scripts/bootstrap_pilot_admin.py

La contraseña NUNCA se imprime ni se persiste en el repo.
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.domains.usuarios.services.users_service import create_user_admin
from app.models import User
from app.security.production_database import PILOT_DATABASE_NAME, database_name_from_uri


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crea usuario ADMIN inicial del piloto.")
    parser.add_argument("--username", default=os.getenv("PILOT_ADMIN_USERNAME", "").strip())
    parser.add_argument("--email", default=os.getenv("PILOT_ADMIN_EMAIL", "").strip())
    parser.add_argument(
        "--password",
        default=os.getenv("PILOT_ADMIN_PASSWORD", "").strip(),
        help="Leer desde env PILOT_ADMIN_PASSWORD (no se loguea).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida entorno sin crear usuario.",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv(os.path.join(BACKEND_ROOT, ".env"))
    args = parse_args()

    if not args.username or not args.email or not args.password:
        print(
            "Faltan credenciales. Defina PILOT_ADMIN_USERNAME, PILOT_ADMIN_EMAIL y "
            "PILOT_ADMIN_PASSWORD (o flags --username/--email/--password).",
            file=sys.stderr,
        )
        return 1
    if len(args.password) < 12:
        print("La contraseña debe tener al menos 12 caracteres.", file=sys.stderr)
        return 1

    app = create_app()
    with app.app_context():
        uri = str(app.config.get("SQLALCHEMY_DATABASE_URI") or "")
        db_name = database_name_from_uri(uri) if uri else ""
        print(f"DATABASE: {db_name}")
        if db_name and db_name != PILOT_DATABASE_NAME:
            print(
                f"ADVERTENCIA: base actual '{db_name}' difiere del nombre piloto "
                f"acordado '{PILOT_DATABASE_NAME}'.",
                file=sys.stderr,
            )

        existing = User.query.filter(
            (User.username == args.username) | (User.email == args.email)
        ).first()
        if existing:
            print(f"Usuario ya existe: id={existing.id} username={existing.username}")
            return 0

        if args.dry_run:
            print("DRY-RUN: usuario admin no creado.")
            return 0

        user_id = create_user_admin(
            username=args.username,
            email=args.email,
            password=args.password,
            role="admin",
        )
        print(f"ADMIN creado: id={user_id} username={args.username} email={args.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
