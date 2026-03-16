"""add orden_trabajo_id to ruta_item

Revision ID: a1f3c9e4d2b7
Revises: f9c4e2a1b7d0
Create Date: 2026-03-16 14:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1f3c9e4d2b7"
down_revision = "f9c4e2a1b7d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ruta_item", sa.Column("orden_trabajo_id", sa.Integer(), nullable=True))
    op.create_index("ix_ruta_item_orden_trabajo_id", "ruta_item", ["orden_trabajo_id"], unique=False)
    op.create_foreign_key(
        "fk_ruta_item_orden_trabajo_id",
        "ruta_item",
        "orden_trabajo",
        ["orden_trabajo_id"],
        ["id"],
        ondelete="SET NULL",
        onupdate="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_ruta_item_orden_trabajo_id", "ruta_item", type_="foreignkey")
    op.drop_index("ix_ruta_item_orden_trabajo_id", table_name="ruta_item")
    op.drop_column("ruta_item", "orden_trabajo_id")
