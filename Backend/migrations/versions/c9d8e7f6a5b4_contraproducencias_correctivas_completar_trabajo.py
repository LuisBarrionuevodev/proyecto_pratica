"""contraproducencias correctivas (Completar trabajo): rubro / dirección

Revision ID: c9d8e7f6a5b4
Revises: a1b2c3d4e5f6
Create Date: 2026-03-30

"""
from __future__ import annotations

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "c9d8e7f6a5b4"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

_NOMBRES = ("NO ES EL RUBRO", "DIRECCION INCORRECTA")


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for nombre in _NOMBRES:
        conn.execute(
            sa.text(
                "INSERT INTO catalog_contraproducencia (nombre, created_at, updated_at) "
                "SELECT :nombre, :ts, :ts "
                "WHERE NOT EXISTS (SELECT 1 FROM catalog_contraproducencia WHERE nombre = :nombre)"
            ),
            {"nombre": nombre, "ts": now},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for nombre in _NOMBRES:
        conn.execute(sa.text("DELETE FROM catalog_contraproducencia WHERE nombre = :nombre"), {"nombre": nombre})
