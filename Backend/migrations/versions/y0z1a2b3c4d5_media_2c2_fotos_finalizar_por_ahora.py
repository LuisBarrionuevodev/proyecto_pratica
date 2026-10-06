"""MEDIA.2C.2 — marca finalizar fotos pendientes por ahora en ruta_item."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "y0z1a2b3c4d5"
down_revision = "x9y0z1a2b3c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ruta_item",
        sa.Column("fotos_pendientes_cerradas_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "ruta_item",
        sa.Column("fotos_pendientes_cerradas_by_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_ruta_item_fotos_pend_cerradas_user",
        "ruta_item",
        "users",
        ["fotos_pendientes_cerradas_by_user_id"],
        ["id"],
    )
    op.create_index(
        "ix_ruta_item_fotos_pendientes_cerradas_at",
        "ruta_item",
        ["fotos_pendientes_cerradas_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ruta_item_fotos_pendientes_cerradas_at", table_name="ruta_item")
    op.drop_constraint("fk_ruta_item_fotos_pend_cerradas_user", "ruta_item", type_="foreignkey")
    op.drop_column("ruta_item", "fotos_pendientes_cerradas_by_user_id")
    op.drop_column("ruta_item", "fotos_pendientes_cerradas_at")
