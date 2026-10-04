"""V1.1-ACTA-SEGUIMIENTO.1: solicitud carnet y resultado reinspección notificación.

Revision ID: q7r8s9t0u1v2
Revises: p1q2r3s4t5u6
Create Date: 2026-10-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "q7r8s9t0u1v2"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "solicitud_carnet_manipulador",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contribuyente_id", sa.Integer(), nullable=False),
        sa.Column("inspeccion_id", sa.Integer(), nullable=False),
        sa.Column("solicita_carnet", sa.Boolean(), nullable=False),
        sa.Column("telefono_contacto", sa.String(length=32), nullable=True),
        sa.Column("fecha_solicitud", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contribuyente_id"],
            ["contribuyente.id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["inspeccion_id"],
            ["inspeccion.id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inspeccion_id", name="uq_solicitud_carnet_inspeccion_id"),
    )
    op.create_index(
        "ix_solicitud_carnet_contribuyente_id",
        "solicitud_carnet_manipulador",
        ["contribuyente_id"],
        unique=False,
    )

    op.create_table(
        "notificacion_resultado_reinspeccion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notificacion_id", sa.Integer(), nullable=False),
        sa.Column("actuacion_id", sa.Integer(), nullable=False),
        sa.Column("inspeccion_id", sa.Integer(), nullable=True),
        sa.Column("faltas_subsanadas", sa.Boolean(), nullable=False),
        sa.Column("fecha_verificacion", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["notificacion_id"],
            ["notificacion.id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actuacion_id"],
            ["actuaciones.id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["inspeccion_id"],
            ["inspeccion.id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("actuacion_id", name="uq_notif_resultado_reinspeccion_actuacion_id"),
    )
    op.create_index(
        "ix_notif_resultado_reinspeccion_notificacion_id",
        "notificacion_resultado_reinspeccion",
        ["notificacion_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notif_resultado_reinspeccion_notificacion_id",
        table_name="notificacion_resultado_reinspeccion",
    )
    op.drop_table("notificacion_resultado_reinspeccion")
    op.drop_index("ix_solicitud_carnet_contribuyente_id", table_name="solicitud_carnet_manipulador")
    op.drop_table("solicitud_carnet_manipulador")
