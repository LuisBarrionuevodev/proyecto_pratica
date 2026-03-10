"""add oficio.fecha_oficio and expand oficio.causa

Revision ID: a9d3c7e5b2f1
Revises: f2b6c1d8a4e3
Create Date: 2026-03-10 19:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a9d3c7e5b2f1"
down_revision = "f2b6c1d8a4e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("oficio", sa.Column("fecha_oficio", sa.Date(), nullable=True))
    op.create_index("ix_oficio_fecha_oficio", "oficio", ["fecha_oficio"], unique=False)
    op.alter_column(
        "oficio",
        "causa",
        existing_type=sa.String(length=10),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "oficio",
        "causa",
        existing_type=sa.String(length=255),
        type_=sa.String(length=10),
        existing_nullable=True,
    )
    op.drop_index("ix_oficio_fecha_oficio", table_name="oficio")
    op.drop_column("oficio", "fecha_oficio")
