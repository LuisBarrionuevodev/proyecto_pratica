"""GEO-PERF.1 — cola durable geocode post-commit.

Revision ID: i4j5k6l7m8n9
Revises: h3i4j5k6l7m8
Create Date: 2026-09-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "i4j5k6l7m8n9"
down_revision = "h3i4j5k6l7m8"
branch_labels = None
depends_on = None

_STATUS_ENUM = sa.Enum(
    "pending",
    "processing",
    "done",
    "failed",
    name="geocode_post_commit_job_status",
)


def upgrade() -> None:
    _STATUS_ENUM.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "geocode_post_commit_job",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("domicilio_id", sa.Integer(), nullable=False),
        sa.Column("status", _STATUS_ENUM, nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["domicilio_id"], ["domicilio.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_geocode_post_commit_job_domicilio_id",
        "geocode_post_commit_job",
        ["domicilio_id"],
    )
    op.create_index(
        "ix_geocode_post_commit_job_status",
        "geocode_post_commit_job",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_geocode_post_commit_job_status", table_name="geocode_post_commit_job")
    op.drop_index("ix_geocode_post_commit_job_domicilio_id", table_name="geocode_post_commit_job")
    op.drop_table("geocode_post_commit_job")
    _STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
