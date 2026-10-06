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


def _deduplicate_ruta_item_archivo_by_content_sha() -> None:
    """
    Elimina vínculos redundantes antes del índice único.

    Por grupo (ruta_item_id, categoria, content_sha256) con SHA no nulo conserva una fila:
    1) relación cuyo archivo esté READY;
    2) si no hay READY, menor ruta_item_archivo.id.

    Solo borra filas de ruta_item_archivo; no toca archivo ni storage.
    """
    op.execute(
        """
        DELETE FROM ruta_item_archivo
        WHERE content_sha256 IS NOT NULL
          AND id IN (
            SELECT victim_id FROM (
              SELECT ria1.id AS victim_id
              FROM ruta_item_archivo ria1
              INNER JOIN archivo a1 ON a1.id = ria1.archivo_id
              WHERE ria1.content_sha256 IS NOT NULL
                AND EXISTS (
                  SELECT 1
                  FROM ruta_item_archivo ria2
                  INNER JOIN archivo a2 ON a2.id = ria2.archivo_id
                  WHERE ria2.ruta_item_id = ria1.ruta_item_id
                    AND ria2.categoria = ria1.categoria
                    AND ria2.content_sha256 = ria1.content_sha256
                    AND (
                      (CASE WHEN a2.status = 'READY' THEN 0 ELSE 1 END)
                        < (CASE WHEN a1.status = 'READY' THEN 0 ELSE 1 END)
                      OR (
                        (CASE WHEN a2.status = 'READY' THEN 0 ELSE 1 END)
                          = (CASE WHEN a1.status = 'READY' THEN 0 ELSE 1 END)
                        AND ria2.id < ria1.id
                      )
                    )
                )
            ) AS to_delete
          )
        """
    )


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
    _deduplicate_ruta_item_archivo_by_content_sha()
    op.create_index(
        "uq_ruta_item_archivo_item_cat_sha",
        "ruta_item_archivo",
        ["ruta_item_id", "categoria", "content_sha256"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_ruta_item_archivo_item_cat_sha", table_name="ruta_item_archivo")
    op.drop_column("ruta_item_archivo", "content_sha256")
