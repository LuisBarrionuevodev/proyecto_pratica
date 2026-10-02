"""V1.1-INSPECTOR.1: vínculo opcional users.inspector_id → inspector.

Revision ID: p1q2r3s4t5u6
Revises: o0p1q2r3s4t5
Create Date: 2026-10-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "p1q2r3s4t5u6"
down_revision = "o0p1q2r3s4t5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("inspector_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_users_inspector_id",
            "inspector",
            ["inspector_id"],
            ["id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        )
        batch_op.create_index("uq_users_inspector_id", ["inspector_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("uq_users_inspector_id")
        batch_op.drop_constraint("fk_users_inspector_id", type_="foreignkey")
        batch_op.drop_column("inspector_id")
