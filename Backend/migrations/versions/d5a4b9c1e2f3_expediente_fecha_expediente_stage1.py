"""add expediente.fecha_expediente (stage 1 nullable + backfill)

Revision ID: d5a4b9c1e2f3
Revises: a9d3c7e5b2f1
Create Date: 2026-03-11 15:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d5a4b9c1e2f3"
down_revision = "a9d3c7e5b2f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("expediente", sa.Column("fecha_expediente", sa.Date(), nullable=True))
    op.create_index("ix_expediente_fecha_expediente", "expediente", ["fecha_expediente"], unique=False)
    # Stage 1 backfill: usar fecha administrativa mínima basada en created_at.
    op.execute("UPDATE expediente SET fecha_expediente = DATE(created_at) WHERE fecha_expediente IS NULL")


def downgrade() -> None:
    op.drop_index("ix_expediente_fecha_expediente", table_name="expediente")
    op.drop_column("expediente", "fecha_expediente")

