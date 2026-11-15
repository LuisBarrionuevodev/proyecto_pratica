"""V1.1-ESTABLECIMIENTOS-CUIT.1: reserva única de documento normalizado.

Revision ID: h1i2j3k4l5m6
Revises: g9h0i1j2k3l4
Create Date: 2026-11-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "h1i2j3k4l5m6"
down_revision = "g9h0i1j2k3l4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crea la reserva de CUIT/DNI normalizado usada por la corrección A2."""
    op.create_table(
        "contribuyente_documento_unico",
        sa.Column("documento_normalizado", sa.String(length=32), nullable=False),
        sa.Column("contribuyente_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.ForeignKeyConstraint(
            ["contribuyente_id"],
            ["contribuyente.id"],
            name="fk_contrib_doc_unico_contrib_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("documento_normalizado"),
    )
    op.create_index(
        "ix_contribuyente_documento_unico_contribuyente_id",
        "contribuyente_documento_unico",
        ["contribuyente_id"],
        unique=False,
    )


def downgrade() -> None:
    """Elimina la reserva de documento normalizado."""
    op.drop_index(
        "ix_contribuyente_documento_unico_contribuyente_id",
        table_name="contribuyente_documento_unico",
    )
    op.drop_table("contribuyente_documento_unico")
