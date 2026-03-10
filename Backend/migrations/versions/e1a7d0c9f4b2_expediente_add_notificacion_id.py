"""add expediente.notificacion_id

Revision ID: e1a7d0c9f4b2
Revises: c4d9f2a1b8e7
Create Date: 2026-03-10 17:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e1a7d0c9f4b2"
down_revision = "c4d9f2a1b8e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("expediente", sa.Column("notificacion_id", sa.Integer(), nullable=True))
    op.create_index(
        "ix_expediente_notificacion_id",
        "expediente",
        ["notificacion_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_expediente_notificacion_id",
        "expediente",
        "notificacion",
        ["notificacion_id"],
        ["id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_expediente_notificacion_id", "expediente", type_="foreignkey")
    op.drop_index("ix_expediente_notificacion_id", table_name="expediente")
    op.drop_column("expediente", "notificacion_id")
