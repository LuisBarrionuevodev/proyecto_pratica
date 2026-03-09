"""add deleted_at to domicilio_geocode

Revision ID: e12f4a8b9c31
Revises: ab3f9d7c21e4
Create Date: 2026-03-09 00:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e12f4a8b9c31"
down_revision = "ab3f9d7c21e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("domicilio_geocode", schema=None) as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_domicilio_geocode_deleted_at"),
            ["deleted_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("domicilio_geocode", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_domicilio_geocode_deleted_at"))
        batch_op.drop_column("deleted_at")

