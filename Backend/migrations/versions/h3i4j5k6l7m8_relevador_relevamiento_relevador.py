"""RELEVADORES.1: catálogo relevador y junction relevamiento_relevador.

Revision ID: h3i4j5k6l7m8
Revises: b1c2d3e4f5a6
Create Date: 2026-09-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "h3i4j5k6l7m8"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "relevador",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=128), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_index("ix_relevador_nombre", "relevador", ["nombre"], unique=False)

    op.create_table(
        "relevamiento_relevador",
        sa.Column("relevamiento_id", sa.Integer(), nullable=False),
        sa.Column("relevador_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["relevador_id"], ["relevador.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["relevamiento_id"], ["relevamiento.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("relevamiento_id", "relevador_id"),
    )
    op.create_index(
        "ix_relevamiento_relevador_relevador_id",
        "relevamiento_relevador",
        ["relevador_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_relevamiento_relevador_relevador_id", table_name="relevamiento_relevador")
    op.drop_table("relevamiento_relevador")
    op.drop_index("ix_relevador_nombre", table_name="relevador")
    op.drop_table("relevador")
