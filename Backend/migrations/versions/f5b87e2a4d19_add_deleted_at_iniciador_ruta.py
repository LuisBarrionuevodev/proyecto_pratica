"""add deleted_at to iniciador_ruta

Revision ID: f5b87e2a4d19
Revises: e12f4a8b9c31
Create Date: 2026-03-09 00:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f5b87e2a4d19"
down_revision = "e12f4a8b9c31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("iniciador_ruta", schema=None) as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_iniciador_ruta_deleted_at"),
            ["deleted_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("iniciador_ruta", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_deleted_at"))
        batch_op.drop_column("deleted_at")

