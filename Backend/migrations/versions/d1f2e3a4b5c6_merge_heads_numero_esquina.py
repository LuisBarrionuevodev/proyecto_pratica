"""merge heads numero esquina

Revision ID: d1f2e3a4b5c6
Revises: b8f4a1c2d3e4, 278c6ce2e633
Create Date: 2026-02-01 11:05:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "d1f2e3a4b5c6"
down_revision = ("b8f4a1c2d3e4", "278c6ce2e633")
branch_labels = None
depends_on = None


def upgrade():
    """
    Merge de dos heads en una sola línea.
    """
    pass


def downgrade():
    """
    Downgrade sin cambios (merge).
    """
    pass
