"""establecimiento_operativo + actuaciones.establecimiento_operativo_id

Ficha operativa bromatológica 1:1 con domicilio; vínculo opcional desde actuaciones.
No modifica la tabla legacy `establecimientos`.

Revision ID: a1b2c3d4e5f6
Revises: f1e2d3c4b5a6
Create Date: 2026-03-30

"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "f1e2d3c4b5a6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "establecimiento_operativo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("domicilio_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
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
            ["domicilio_id"],
            ["domicilio.id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domicilio_id", name="uq_establecimiento_operativo_domicilio_id"),
    )
    op.create_index(
        "ix_establecimiento_operativo_created_by_user_id",
        "establecimiento_operativo",
        ["created_by_user_id"],
        unique=False,
    )

    op.add_column(
        "actuaciones",
        sa.Column("establecimiento_operativo_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_actuaciones_establecimiento_operativo_id",
        "actuaciones",
        ["establecimiento_operativo_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_actuaciones_establecimiento_operativo_id",
        "actuaciones",
        "establecimiento_operativo",
        ["establecimiento_operativo_id"],
        ["id"],
        ondelete="SET NULL",
        onupdate="CASCADE",
    )


def downgrade():
    op.drop_constraint("fk_actuaciones_establecimiento_operativo_id", "actuaciones", type_="foreignkey")
    op.drop_index("ix_actuaciones_establecimiento_operativo_id", table_name="actuaciones")
    op.drop_column("actuaciones", "establecimiento_operativo_id")

    op.drop_index("ix_establecimiento_operativo_created_by_user_id", table_name="establecimiento_operativo")
    op.drop_table("establecimiento_operativo")
