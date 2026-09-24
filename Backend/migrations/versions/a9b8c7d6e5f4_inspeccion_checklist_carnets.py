"""inspeccion checklist + cantidad_carnets_sanidad (INSPECCIÓN-CHECKLIST.1).

Revision ID: a9b8c7d6e5f4
Revises: f2a3b4c5d6e7
Create Date: 2026-09-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a9b8c7d6e5f4"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None

_SEEDS = [
    (1, "TIENE_BANO", "Tiene baño", 1),
    (2, "TIENE_SALON", "Tiene salón", 2),
    (3, "TIENE_DEPOSITO", "Tiene depósito", 3),
    (4, "TIENE_COCINA_MESA_TRABAJO", "Tiene cocina / mesa de trabajo", 4),
]


def upgrade() -> None:
    op.create_table(
        "item_acta_inspeccion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=64), nullable=False),
        sa.Column("nombre", sa.String(length=128), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo", name="uq_item_acta_inspeccion_codigo"),
    )
    op.create_index("ix_item_acta_inspeccion_orden", "item_acta_inspeccion", ["orden"])

    op.create_table(
        "acta_inspeccion_item",
        sa.Column("acta_inspeccion_id", sa.Integer(), nullable=False),
        sa.Column("item_acta_inspeccion_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["acta_inspeccion_id"], ["inspeccion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["item_acta_inspeccion_id"], ["item_acta_inspeccion.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("acta_inspeccion_id", "item_acta_inspeccion_id"),
        sa.UniqueConstraint(
            "acta_inspeccion_id",
            "item_acta_inspeccion_id",
            name="uq_acta_inspeccion_item",
        ),
    )
    op.create_index(
        "ix_acta_inspeccion_item_item_id",
        "acta_inspeccion_item",
        ["item_acta_inspeccion_id"],
    )

    op.add_column(
        "inspeccion",
        sa.Column(
            "cantidad_carnets_sanidad",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    item_table = sa.table(
        "item_acta_inspeccion",
        sa.column("id", sa.Integer),
        sa.column("codigo", sa.String),
        sa.column("nombre", sa.String),
        sa.column("activo", sa.Boolean),
        sa.column("orden", sa.Integer),
    )
    op.bulk_insert(
        item_table,
        [
            {"id": sid, "codigo": codigo, "nombre": nombre, "activo": True, "orden": orden}
            for sid, codigo, nombre, orden in _SEEDS
        ],
    )


def downgrade() -> None:
    op.drop_column("inspeccion", "cantidad_carnets_sanidad")
    op.drop_index("ix_acta_inspeccion_item_item_id", table_name="acta_inspeccion_item")
    op.drop_table("acta_inspeccion_item")
    op.drop_index("ix_item_acta_inspeccion_orden", table_name="item_acta_inspeccion")
    op.drop_table("item_acta_inspeccion")
