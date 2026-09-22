#!/usr/bin/env python
"""Smoke QA post FASE 2C.2B' apply (read-only GETs)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from flask_jwt_extended import create_access_token
from sqlalchemy import text

from app.database import db
from app.main import create_app


def main() -> None:
    app = create_app()
    results: dict = {}
    with app.app_context():
        admin_id = db.session.execute(
            text("SELECT id FROM users WHERE LOWER(username) = 'admin' LIMIT 1")
        ).scalar()
        token = create_access_token(
            identity=str(admin_id), additional_claims={"role": "admin"}
        )
        headers = {"Authorization": f"Bearer {token}"}

    client = app.test_client()
    endpoints = [
        ("profile_me", "/api/profile/me"),
        ("actuaciones_search", "/actuaciones/search?q=20&limit=5"),
        ("rutas_list", "/rutas-trabajo"),
        ("denuncias", "/api/denuncias?limit=5"),
        ("catalogos_rubros", "/catalogos/rubros"),
        ("relevamientos", "/relevamientos"),
    ]
    for key, path in endpoints:
        r = client.get(path, headers=headers)
        entry = {"status": r.status_code, "ok": r.status_code == 200}
        if key == "relevamientos" and r.status_code == 500:
            entry["flag"] = "RELEVAMIENTOS-500-PREDEPLOY"
        results[key] = entry

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
