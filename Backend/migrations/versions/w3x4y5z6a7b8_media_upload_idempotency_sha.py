"""V1.1-MEDIA.2A: idempotencia upload (ruta_item + categoría + sha256).

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "w3x4y5z6a7b8"
down_revision = "v2w3x4y5z6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ruta_item_archivo",
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
    )
    op.execute(
        """
        UPDATE ruta_item_archivo ria
        INNER JOIN archivo a ON a.id = ria.archivo_id
        SET ria.content_sha256 = LOWER(a.sha256)
        WHERE ria.content_sha256 IS NULL
        """
    )
    op.create_index(
        "uq_ruta_item_archivo_item_cat_sha",
        "ruta_item_archivo",
        ["ruta_item_id", "categoria", "content_sha256"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_ruta_item_archivo_item_cat_sha", table_name="ruta_item_archivo")
    op.drop_column("ruta_item_archivo", "content_sha256")
