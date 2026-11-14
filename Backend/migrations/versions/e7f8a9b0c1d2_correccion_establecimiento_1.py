"""V1.1-ESTABLECIMIENTOS-EDICION.1: auditoría de correcciones desde la ficha.

Revision ID: e7f8a9b0c1d2
Revises: d5e6f7a8b9c0
Create Date: 2026-11-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e7f8a9b0c1d2"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "correccion_establecimiento_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("establecimiento_operativo_id", sa.Integer(), nullable=False),
        sa.Column("contribuyente_id", sa.Integer(), nullable=True),
        sa.Column("domicilio_id", sa.Integer(), nullable=True),
        sa.Column(
            "tipo",
            sa.Enum(
                "CONTRIBUYENTE",
                "DOMICILIO",
                "AMBOS",
                name="correccion_establecimiento_tipo_enum",
            ),
            nullable=False,
        ),
        sa.Column("valores_anteriores", sa.JSON(), nullable=False),
        sa.Column("valores_nuevos", sa.JSON(), nullable=False),
        sa.Column("alcance", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.ForeignKeyConstraint(
            ["establecimiento_operativo_id"],
            ["establecimiento_operativo.id"],
            name="fk_corr_est_audit_eo_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["contribuyente_id"],
            ["contribuyente.id"],
            name="fk_corr_est_audit_contrib_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["domicilio_id"],
            ["domicilio.id"],
            name="fk_corr_est_audit_dom_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_corr_est_audit_user_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_correccion_establecimiento_audit_establecimiento_operativo_id"),
        "correccion_establecimiento_audit",
        ["establecimiento_operativo_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_correccion_establecimiento_audit_contribuyente_id"),
        "correccion_establecimiento_audit",
        ["contribuyente_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_correccion_establecimiento_audit_domicilio_id"),
        "correccion_establecimiento_audit",
        ["domicilio_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_correccion_establecimiento_audit_tipo"),
        "correccion_establecimiento_audit",
        ["tipo"],
        unique=False,
    )
    op.create_index(
        op.f("ix_correccion_establecimiento_audit_created_by_user_id"),
        "correccion_establecimiento_audit",
        ["created_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_correccion_establecimiento_audit_created_by_user_id"),
        table_name="correccion_establecimiento_audit",
    )
    op.drop_index(
        op.f("ix_correccion_establecimiento_audit_tipo"),
        table_name="correccion_establecimiento_audit",
    )
    op.drop_index(
        op.f("ix_correccion_establecimiento_audit_domicilio_id"),
        table_name="correccion_establecimiento_audit",
    )
    op.drop_index(
        op.f("ix_correccion_establecimiento_audit_contribuyente_id"),
        table_name="correccion_establecimiento_audit",
    )
    op.drop_index(
        op.f("ix_correccion_establecimiento_audit_establecimiento_operativo_id"),
        table_name="correccion_establecimiento_audit",
    )
    op.drop_table("correccion_establecimiento_audit")
    sa.Enum(name="correccion_establecimiento_tipo_enum").drop(op.get_bind(), checkfirst=True)
