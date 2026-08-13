"""OPER-RUTA.2: tabla persistente ruta_pool_dia.

Revision ID: c3d4e5f6a7b8
Revises: b7e8f9a0c1d2
Create Date: 2026-08-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b7e8f9a0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ruta_pool_dia",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("turno_id", sa.Integer(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column(
            "origen_tipo",
            sa.Enum(
                "INICIADOR",
                "ACTUACION_NOTIF",
                "ACTUACION_COMP",
                "RELEVAMIENTO",
                "DENUNCIA",
                "MANUAL",
                name="ruta_pool_dia_origen_tipo_enum",
            ),
            nullable=False,
        ),
        sa.Column("iniciador_ruta_id", sa.Integer(), nullable=True),
        sa.Column("actuacion_id", sa.Integer(), nullable=True),
        sa.Column("domicilio_id", sa.Integer(), nullable=False),
        sa.Column("distrito_id", sa.Integer(), nullable=True),
        sa.Column("rubro_id", sa.Integer(), nullable=True),
        sa.Column(
            "estado",
            sa.Enum(
                "EN_POOL",
                "ASIGNADO_A_RUTA",
                "DESCARTADO",
                name="ruta_pool_dia_estado_enum",
            ),
            nullable=False,
            server_default="EN_POOL",
        ),
        sa.Column("ruta_trabajo_id", sa.Integer(), nullable=True),
        sa.Column("ruta_item_id", sa.Integer(), nullable=True),
        sa.Column("observacion", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["actuacion_id"], ["actuaciones.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["distrito_id"], ["distrito.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["domicilio_id"], ["domicilio.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["iniciador_ruta_id"], ["iniciador_ruta.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rubro_id"], ["rubro.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ruta_item_id"], ["ruta_item.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ruta_trabajo_id"], ["ruta_trabajo.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["turno_id"], ["turno.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["usuario_id"], ["users.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ruta_pool_dia_fecha", "ruta_pool_dia", ["fecha"], unique=False)
    op.create_index("ix_ruta_pool_dia_turno_id", "ruta_pool_dia", ["turno_id"], unique=False)
    op.create_index("ix_ruta_pool_dia_usuario_id", "ruta_pool_dia", ["usuario_id"], unique=False)
    op.create_index("ix_ruta_pool_dia_origen_tipo", "ruta_pool_dia", ["origen_tipo"], unique=False)
    op.create_index("ix_ruta_pool_dia_iniciador_ruta_id", "ruta_pool_dia", ["iniciador_ruta_id"], unique=False)
    op.create_index("ix_ruta_pool_dia_actuacion_id", "ruta_pool_dia", ["actuacion_id"], unique=False)
    op.create_index("ix_ruta_pool_dia_domicilio_id", "ruta_pool_dia", ["domicilio_id"], unique=False)
    op.create_index("ix_ruta_pool_dia_distrito_id", "ruta_pool_dia", ["distrito_id"], unique=False)
    op.create_index("ix_ruta_pool_dia_rubro_id", "ruta_pool_dia", ["rubro_id"], unique=False)
    op.create_index("ix_ruta_pool_dia_estado", "ruta_pool_dia", ["estado"], unique=False)
    op.create_index("ix_ruta_pool_dia_ruta_trabajo_id", "ruta_pool_dia", ["ruta_trabajo_id"], unique=False)
    op.create_index("ix_ruta_pool_dia_ruta_item_id", "ruta_pool_dia", ["ruta_item_id"], unique=False)
    op.create_index("ix_ruta_pool_dia_deleted_at", "ruta_pool_dia", ["deleted_at"], unique=False)
    op.create_index(
        "ix_ruta_pool_dia_fecha_estado_distrito_rubro",
        "ruta_pool_dia",
        ["fecha", "estado", "distrito_id", "rubro_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ruta_pool_dia_fecha_estado_distrito_rubro", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_deleted_at", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_ruta_item_id", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_ruta_trabajo_id", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_estado", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_rubro_id", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_distrito_id", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_domicilio_id", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_actuacion_id", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_iniciador_ruta_id", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_origen_tipo", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_usuario_id", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_turno_id", table_name="ruta_pool_dia")
    op.drop_index("ix_ruta_pool_dia_fecha", table_name="ruta_pool_dia")
    op.drop_table("ruta_pool_dia")
