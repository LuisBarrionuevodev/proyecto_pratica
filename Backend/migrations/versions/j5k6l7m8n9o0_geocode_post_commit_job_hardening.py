"""GEO-PERF.1.1 — hardening cola geocode post-commit.

Revision ID: j5k6l7m8n9o0
Revises: i4j5k6l7m8n9
Create Date: 2026-09-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "j5k6l7m8n9o0"
down_revision = "i4j5k6l7m8n9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "geocode_post_commit_job",
        sa.Column("processing_started_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "geocode_post_commit_job",
        sa.Column("claimed_addr_hash", sa.String(length=40), nullable=True),
    )
    op.create_index(
        "ix_geocode_post_commit_job_status_created",
        "geocode_post_commit_job",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_geocode_post_commit_job_domicilio_status",
        "geocode_post_commit_job",
        ["domicilio_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_geocode_post_commit_job_domicilio_status",
        table_name="geocode_post_commit_job",
    )
    op.drop_index(
        "ix_geocode_post_commit_job_status_created",
        table_name="geocode_post_commit_job",
    )
    op.drop_column("geocode_post_commit_job", "claimed_addr_hash")
    op.drop_column("geocode_post_commit_job", "processing_started_at")
