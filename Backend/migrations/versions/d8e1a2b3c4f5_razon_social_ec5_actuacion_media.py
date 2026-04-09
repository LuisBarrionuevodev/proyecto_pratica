"""contrib razon_social, actuaciones ec5_uuid, actuacion_media

Revision ID: d8e1a2b3c4f5
Revises: c52b5c91fb5b
Create Date: 2026-03-30

"""
from alembic import op
import sqlalchemy as sa


revision = "d8e1a2b3c4f5"
down_revision = "c52b5c91fb5b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "contribuyente",
        sa.Column("razon_social", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_contribuyente_razon_social", "contribuyente", ["razon_social"], unique=False)

    op.add_column(
        "actuaciones",
        sa.Column("ec5_uuid", sa.String(length=36), nullable=True),
    )
    op.create_index("ix_actuaciones_ec5_uuid", "actuaciones", ["ec5_uuid"], unique=True)

    op.create_table(
        "actuacion_media",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actuacion_id", sa.Integer(), nullable=False),
        sa.Column("categoria", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("orden", sa.SmallInteger(), nullable=False, server_default="0"),
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
    )
    op.create_index("ix_actuacion_media_actuacion_id", "actuacion_media", ["actuacion_id"], unique=False)


def downgrade():
    op.drop_index("ix_actuacion_media_actuacion_id", table_name="actuacion_media")
    op.drop_table("actuacion_media")
    op.drop_index("ix_actuaciones_ec5_uuid", table_name="actuaciones")
    op.drop_column("actuaciones", "ec5_uuid")
    op.drop_index("ix_contribuyente_razon_social", table_name="contribuyente")
    op.drop_column("contribuyente", "razon_social")
