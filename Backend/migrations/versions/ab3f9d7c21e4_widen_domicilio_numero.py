"""widen domicilio.numero length

Revision ID: ab3f9d7c21e4
Revises: 9a0617e19f38
Create Date: 2026-03-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ab3f9d7c21e4"
down_revision = "9a0617e19f38"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "domicilio",
        "numero",
        existing_type=sa.String(length=20),
        type_=sa.String(length=200),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "domicilio",
        "numero",
        existing_type=sa.String(length=200),
        type_=sa.String(length=20),
        existing_nullable=False,
    )

