"""domicilio add distrito_id

Revision ID: 7a1c2d3e4f5a
Revises: 6f1d2c3b4a5e
Create Date: 2026-02-05 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7a1c2d3e4f5a"
down_revision = "6f1d2c3b4a5e"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("domicilio", schema=None) as batch_op:
        batch_op.add_column(sa.Column("distrito_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_domicilio_distrito_id"), ["distrito_id"], unique=False)
        batch_op.create_foreign_key(
            None,
            "distrito",
            ["distrito_id"],
            ["id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        )


def downgrade():
    with op.batch_alter_table("domicilio", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_domicilio_distrito_id"))
        batch_op.drop_column("distrito_id")
