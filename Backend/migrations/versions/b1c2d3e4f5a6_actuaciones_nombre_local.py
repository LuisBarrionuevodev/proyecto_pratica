"""actuaciones nombre_local (completar trabajo / futuro establecimiento)

Revision ID: b1c2d3e4f5a6
Revises: 450014dac037
Create Date: 2026-03-28

"""
from alembic import op
import sqlalchemy as sa



revision = "b1c2d3e4f5a6"
down_revision = "450014dac037"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "actuaciones",
        sa.Column("nombre_local", sa.String(length=255), nullable=True),
    )


def downgrade():
    op.drop_column("actuaciones", "nombre_local")
