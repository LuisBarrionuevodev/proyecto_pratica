"""ACT-HIST.1 — carga solo comprobación histórica (snapshot titular, OT nullable).

Revision ID: m8n9o0p1q2r3
Revises: l7m8n9o0p1q2
Create Date: 2026-09-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "m8n9o0p1q2r3"
down_revision = "l7m8n9o0p1q2"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def _index_exists(table: str, index: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return index in {i["name"] for i in insp.get_indexes(table)}


def upgrade() -> None:
    if not _column_exists("actuaciones", "carga_solo_comprobacion"):
        with op.batch_alter_table("actuaciones", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "carga_solo_comprobacion",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )
            batch_op.add_column(
                sa.Column("titular_nombre_historico", sa.String(length=128), nullable=True)
            )
            batch_op.add_column(
                sa.Column("titular_apellido_historico", sa.String(length=128), nullable=True)
            )
            batch_op.add_column(
                sa.Column("titular_razon_social_historica", sa.String(length=255), nullable=True)
            )

    with op.batch_alter_table("actuaciones", schema=None) as batch_op:
        batch_op.alter_column("orden_trabajo_id", existing_type=sa.Integer(), nullable=True)

    if not _index_exists("actuaciones", "ix_actuaciones_carga_solo_comprobacion"):
        op.create_index(
            "ix_actuaciones_carga_solo_comprobacion",
            "actuaciones",
            ["carga_solo_comprobacion"],
            unique=False,
        )

    bind = op.get_bind()
    insp = inspect(bind)
    checks = {c["name"] for c in insp.get_check_constraints("actuaciones")}
    # MySQL no permite CHECK sobre orden_trabajo_id (columna FK) → regla OT en aplicación.
    if "ck_act_hist_titular" not in checks:
        op.create_check_constraint(
            "ck_act_hist_titular",
            "actuaciones",
            "carga_solo_comprobacion = 0 OR ("
            "(titular_razon_social_historica IS NOT NULL "
            "AND TRIM(titular_razon_social_historica) <> '') OR ("
            "titular_nombre_historico IS NOT NULL AND TRIM(titular_nombre_historico) <> '' "
            "AND titular_apellido_historico IS NOT NULL AND TRIM(titular_apellido_historico) <> ''"
            "))",
        )


def downgrade() -> None:
    op.drop_constraint("ck_act_hist_titular", "actuaciones", type_="check")
    op.drop_index("ix_actuaciones_carga_solo_comprobacion", table_name="actuaciones")

    with op.batch_alter_table("actuaciones", schema=None) as batch_op:
        batch_op.drop_column("titular_razon_social_historica")
        batch_op.drop_column("titular_apellido_historico")
        batch_op.drop_column("titular_nombre_historico")
        batch_op.drop_column("carga_solo_comprobacion")
        batch_op.alter_column("orden_trabajo_id", existing_type=sa.Integer(), nullable=False)
