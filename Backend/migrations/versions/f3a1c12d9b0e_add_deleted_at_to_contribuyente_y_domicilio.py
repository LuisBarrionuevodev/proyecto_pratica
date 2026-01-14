"""add deleted_at to contribuyente y domicilio

Revision ID: f3a1c12d9b0e
Revises: 95e818773d26
Create Date: 2026-01-14 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = "f3a1c12d9b0e"
down_revision = "95e818773d26"
branch_labels = None
depends_on = None


def upgrade():
    """Agregar columnas nullable `deleted_at` para soft delete."""
    op.add_column("domicilio", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column(
        "contribuyente", sa.Column("deleted_at", sa.DateTime(), nullable=True)
    )


def downgrade():
    """Quitar columnas `deleted_at`."""
    op.drop_column("contribuyente", "deleted_at")
    op.drop_column("domicilio", "deleted_at")

