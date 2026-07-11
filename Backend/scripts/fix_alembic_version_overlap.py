"""Corrige alembic_version con dos filas (overlap 05a3 + c9d8). Uso único local."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.database import db

app = create_app()

with app.app_context():
    rows = db.session.execute(db.text("SELECT version_num FROM alembic_version")).fetchall()
    print("antes:", rows)
    if ("05a3b9d35a32",) in rows and ("c9d8e7f6a5b4",) in rows:
        db.session.execute(
            db.text("DELETE FROM alembic_version WHERE version_num = '05a3b9d35a32'")
        )
        db.session.commit()
        print("eliminada fila obsoleta 05a3b9d35a32")
    rows = db.session.execute(db.text("SELECT version_num FROM alembic_version")).fetchall()
    print("despues:", rows)
