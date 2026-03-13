"""add soft delete fields to ruta_grupo and ruta_item (stage 1)

Revision ID: f9c4e2a1b7d0
Revises: e7c2a1b4d9f0
Create Date: 2026-03-13 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f9c4e2a1b7d0"
down_revision = "e7c2a1b4d9f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ruta_grupo", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_ruta_grupo_deleted_at", "ruta_grupo", ["deleted_at"], unique=False)

    op.add_column("ruta_item", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_ruta_item_deleted_at", "ruta_item", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ruta_item_deleted_at", table_name="ruta_item")
    op.drop_column("ruta_item", "deleted_at")

    op.drop_index("ix_ruta_grupo_deleted_at", table_name="ruta_grupo")
    op.drop_column("ruta_grupo", "deleted_at")
