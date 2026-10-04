"""V1.1-ACTA-SEGUIMIENTO.1B: auditoría en tablas de seguimiento de acta.

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-10-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "r8s9t0u1v2w3"
down_revision = "q7r8s9t0u1v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("solicitud_carnet_manipulador", "notificacion_resultado_reinspeccion"):
        op.add_column(
            table,
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=True,
            ),
        )
        op.add_column(
            table,
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            f"fk_{table}_updated_by_user_id_users",
            table,
            "users",
            ["updated_by_user_id"],
            ["id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        )
        op.create_index(
            op.f(f"ix_{table}_updated_by_user_id"),
            table,
            ["updated_by_user_id"],
            unique=False,
        )


def downgrade() -> None:
    for table in ("notificacion_resultado_reinspeccion", "solicitud_carnet_manipulador"):
        op.drop_index(op.f(f"ix_{table}_updated_by_user_id"), table_name=table)
        op.drop_constraint(
            f"fk_{table}_updated_by_user_id_users",
            table,
            type_="foreignkey",
        )
        op.drop_column(table, "updated_by_user_id")
        op.drop_column(table, "updated_at")
