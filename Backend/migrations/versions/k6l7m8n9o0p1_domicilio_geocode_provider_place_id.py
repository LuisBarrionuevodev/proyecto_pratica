"""GEO-GOOGLE.2 — provider_place_id en domicilio_geocode.

Revision ID: k6l7m8n9o0p1
Revises: j5k6l7m8n9o0
Create Date: 2026-09-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "k6l7m8n9o0p1"
down_revision = "j5k6l7m8n9o0"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c["name"] for c in inspect(bind).get_columns(table)}


def upgrade() -> None:
    if not _has_column("domicilio_geocode", "provider_place_id"):
        op.add_column(
            "domicilio_geocode",
            sa.Column("provider_place_id", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    if _has_column("domicilio_geocode", "provider_place_id"):
        op.drop_column("domicilio_geocode", "provider_place_id")
