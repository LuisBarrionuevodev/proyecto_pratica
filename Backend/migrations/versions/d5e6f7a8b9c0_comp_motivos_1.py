"""V1.1-COMP-MOTIVOS.1 — puente comprobacion_motivo y backfill exacto.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-11-09

Preflight (antes de Railway / prod): correr el SQL de control del relevamiento
MOTIVOS.0 (apéndice A) sobre el dump real e informar totales, vacío/NULL,
PENDIENTE, coincidencias exactas y valores sin coincidencia. Los sin coincidencia
no bloquean el deploy: quedan sin vínculo y conservan `comprobacion.motivo`.

El downgrade elimina solo la tabla puente; no toca el texto histórico.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crea `comprobacion_motivo` y vincula coincidencias exactas de catálogo."""
    op.create_table(
        "comprobacion_motivo",
        sa.Column("comprobacion_id", sa.Integer(), nullable=False),
        sa.Column("catalog_motivo_comprobacion_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["comprobacion_id"],
            ["comprobacion.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["catalog_motivo_comprobacion_id"],
            ["catalog_motivo_comprobacion.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "comprobacion_id",
            "catalog_motivo_comprobacion_id",
        ),
    )
    bind = op.get_bind()
    bind.execute(
        text(
            """
            INSERT INTO comprobacion_motivo (
                comprobacion_id,
                catalog_motivo_comprobacion_id,
                created_at,
                updated_at
            )
            SELECT
                c.id,
                cat.id,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM comprobacion AS c
            INNER JOIN catalog_motivo_comprobacion AS cat
                ON cat.nombre = TRIM(c.motivo)
            WHERE c.motivo IS NOT NULL
              AND TRIM(c.motivo) <> ''
              AND UPPER(TRIM(c.motivo)) <> 'PENDIENTE'
            """
        )
    )


def downgrade() -> None:
    """Elimina la puente. Conserva íntegro `comprobacion.motivo`."""
    op.drop_table("comprobacion_motivo")
