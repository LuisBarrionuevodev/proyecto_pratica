"""V1.1-MEDIA.2B: idempotencia cierre Completar trabajo + flag evidencias pendientes.

Revision ID: x9y0z1a2b3c4
Revises: w3x4y5z6a7b8
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "x9y0z1a2b3c4"
down_revision = "w3x4y5z6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ruta_item",
        sa.Column(
            "evidencias_pendientes_abiertas",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_table(
        "completar_trabajo_cierre_idempotency",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruta_item_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ruta_item_id"],
            ["ruta_item.id"],
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ruta_item_id",
            "idempotency_key",
            name="uq_completar_trabajo_cierre_idem_item_key",
        ),
    )
    op.create_index(
        "ix_completar_trabajo_cierre_idem_ruta_item",
        "completar_trabajo_cierre_idempotency",
        ["ruta_item_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    table_names = set(insp.get_table_names())
    if "completar_trabajo_cierre_idempotency" in table_names:
        index_names = {idx["name"] for idx in insp.get_indexes("completar_trabajo_cierre_idempotency")}
        if "ix_completar_trabajo_cierre_idem_ruta_item" in index_names:
            op.drop_index(
                "ix_completar_trabajo_cierre_idem_ruta_item",
                table_name="completar_trabajo_cierre_idempotency",
            )
        op.drop_table("completar_trabajo_cierre_idempotency")
    ruta_cols = {c["name"] for c in insp.get_columns("ruta_item")}
    if "evidencias_pendientes_abiertas" in ruta_cols:
        op.drop_column("ruta_item", "evidencias_pendientes_abiertas")
