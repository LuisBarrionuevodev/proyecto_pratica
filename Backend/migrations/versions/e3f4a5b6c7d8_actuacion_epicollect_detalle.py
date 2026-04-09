"""tabla actuacion_epicollect_detalle (JSON no-media)

Revision ID: e3f4a5b6c7d8
Revises: d8e1a2b3c4f5
Create Date: 2026-03-31

"""
from alembic import op
import sqlalchemy as sa


revision = "e3f4a5b6c7d8"
down_revision = "d8e1a2b3c4f5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "actuacion_epicollect_detalle",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actuacion_id", sa.Integer(), nullable=False),
        sa.Column("entry_uuid", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="EPICOLLECT"),
        sa.Column("payload_non_media", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["actuacion_id"],
            ["actuaciones.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("actuacion_id", name="uq_actuacion_epicollect_detalle_actuacion_id"),
    )
    op.create_index(
        "ix_actuacion_epicollect_detalle_entry_uuid",
        "actuacion_epicollect_detalle",
        ["entry_uuid"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_actuacion_epicollect_detalle_entry_uuid", table_name="actuacion_epicollect_detalle")
    op.drop_table("actuacion_epicollect_detalle")
