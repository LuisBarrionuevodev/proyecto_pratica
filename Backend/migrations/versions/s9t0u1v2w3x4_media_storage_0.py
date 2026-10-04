"""V1.1-MEDIA.0: metadata de archivos y vínculo con ruta_item.

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-10-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "s9t0u1v2w3x4"
down_revision = "r8s9t0u1v2w3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "archivo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storage_provider", sa.String(length=32), nullable=False),
        sa.Column("bucket", sa.String(length=128), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "READY",
                "REJECTED",
                "DELETED",
                name="archivo_status_enum",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key", name="uq_archivo_object_key"),
    )
    op.create_index("ix_archivo_status", "archivo", ["status"], unique=False)
    op.create_index("ix_archivo_uploaded_by_user_id", "archivo", ["uploaded_by_user_id"], unique=False)

    op.create_table(
        "ruta_item_archivo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruta_item_id", sa.Integer(), nullable=False),
        sa.Column("archivo_id", sa.Integer(), nullable=False),
        sa.Column(
            "categoria",
            sa.Enum(
                "ACTA_DOCUMENTACION",
                "FOTO_INSPECCION",
                name="ruta_item_archivo_categoria_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "tipo_documento",
            sa.Enum(
                "ACTA_INSPECCION",
                "ACTA_NOTIFICACION",
                "OTRO_DOCUMENTO",
                name="ruta_item_archivo_tipo_documento_enum",
            ),
            nullable=True,
        ),
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
            ["archivo_id"],
            ["archivo.id"],
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ruta_item_id", "archivo_id", name="uq_ruta_item_archivo_pair"),
    )
    op.create_index("ix_ruta_item_archivo_ruta_item_id", "ruta_item_archivo", ["ruta_item_id"], unique=False)
    op.create_index("ix_ruta_item_archivo_archivo_id", "ruta_item_archivo", ["archivo_id"], unique=False)
    op.create_index("ix_ruta_item_archivo_categoria", "ruta_item_archivo", ["categoria"], unique=False)
    op.create_index(
        "ix_ruta_item_archivo_item_categoria",
        "ruta_item_archivo",
        ["ruta_item_id", "categoria"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ruta_item_archivo_item_categoria", table_name="ruta_item_archivo")
    op.drop_index("ix_ruta_item_archivo_categoria", table_name="ruta_item_archivo")
    op.drop_index("ix_ruta_item_archivo_archivo_id", table_name="ruta_item_archivo")
    op.drop_index("ix_ruta_item_archivo_ruta_item_id", table_name="ruta_item_archivo")
    op.drop_table("ruta_item_archivo")
    op.drop_index("ix_archivo_uploaded_by_user_id", table_name="archivo")
    op.drop_index("ix_archivo_status", table_name="archivo")
    op.drop_table("archivo")
