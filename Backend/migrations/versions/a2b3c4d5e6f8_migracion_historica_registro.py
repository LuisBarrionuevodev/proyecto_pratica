"""V1.1-MIG-ACTAS.1A — tabla migracion_historica_registro.

Revision ID: a2b3c4d5e6f8
Revises: z1a2b3c4d5e6
Create Date: 2026-10-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a2b3c4d5e6f8"
down_revision = "z1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "migracion_historica_registro",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_record_uuid", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("target_actuacion_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_detail_sanitized", sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_name",
            "source_sha256",
            "source_record_uuid",
            name="uq_migracion_hist_fuente_uuid",
        ),
    )
    op.create_index(
        "ix_migracion_historica_registro_batch_id",
        "migracion_historica_registro",
        ["batch_id"],
    )
    op.create_index(
        "ix_migracion_historica_registro_source_name",
        "migracion_historica_registro",
        ["source_name"],
    )
    op.create_index(
        "ix_migracion_historica_registro_source_sha256",
        "migracion_historica_registro",
        ["source_sha256"],
    )
    op.create_index(
        "ix_migracion_historica_registro_source_record_uuid",
        "migracion_historica_registro",
        ["source_record_uuid"],
    )
    op.create_index(
        "ix_migracion_historica_registro_decision",
        "migracion_historica_registro",
        ["decision"],
    )
    op.create_index(
        "ix_migracion_historica_registro_target_actuacion_id",
        "migracion_historica_registro",
        ["target_actuacion_id"],
    )


def downgrade() -> None:
    op.drop_table("migracion_historica_registro")
