"""V1.1-MEDIA.1A: auditoría de eliminación en archivo.

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2026-10-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "u1v2w3x4y5z6"
down_revision = "t0u1v2w3x4y5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("archivo", sa.Column("deleted_by_user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_archivo_deleted_by_user_id",
        "archivo",
        "users",
        ["deleted_by_user_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="SET NULL",
    )
    op.create_index("ix_archivo_deleted_by_user_id", "archivo", ["deleted_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_archivo_deleted_by_user_id", table_name="archivo")
    op.drop_constraint("fk_archivo_deleted_by_user_id", "archivo", type_="foreignkey")
    op.drop_column("archivo", "deleted_by_user_id")
