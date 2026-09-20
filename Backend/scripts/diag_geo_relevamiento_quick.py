"""Diagnóstico rápido: provider + últimos geocodes y jobs."""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app import create_app
from app.database import db
from app.domains.geolocalizacion.geocoding.services.geocode_service import get_geocoder_provider

app = create_app()
with app.app_context():
    import os

    print("GEOCODER_PROVIDER config:", app.config.get("GEOCODER_PROVIDER"))
    print("get_geocoder_provider():", get_geocoder_provider())
    key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    print("GOOGLE_MAPS_API_KEY set:", bool(key), "len:", len(key))

    rows = db.session.execute(
        text(
            """
            SELECT dg.domicilio_id, dg.geo_status, dg.provider, dg.quality,
                   dg.error_msg, dg.checked_at, d.calle, d.numero, d.calle_norm_status
            FROM domicilio_geocode dg
            JOIN domicilio d ON d.id = dg.domicilio_id
            ORDER BY COALESCE(dg.checked_at, dg.updated_at) DESC
            LIMIT 8
            """
        )
    ).mappings().all()
    print("\n--- recent geocode ---")
    for r in rows:
        print(dict(r))

    jobs = db.session.execute(
        text(
            """
            SELECT id, domicilio_id, status, attempts, last_error, updated_at
            FROM geocode_post_commit_job
            ORDER BY id DESC LIMIT 8
            """
        )
    ).mappings().all()
    print("\n--- recent jobs ---")
    for j in jobs:
        print(dict(j))
