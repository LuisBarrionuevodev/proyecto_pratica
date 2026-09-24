"""OT-AUTO.3 — secuencia global OT automática al publicar.

Revision ID: o0p1q2r3s4t5
Revises: n9o0p1q2r3s4
Create Date: 2026-09-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "o0p1q2r3s4t5"
down_revision = "n9o0p1q2r3s4"
branch_labels = None
depends_on = None

_DEFAULT_SEED = 89862
_DEFAULT_SEED_DISPLAY = "089862"


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return table in insp.get_table_names()


def _precheck_seed(bind) -> dict:
    """Read-only: aborta seed si el display propuesto ya está ocupado."""
    row = bind.execute(
        text(
            """
            SELECT COUNT(*) AS cnt
            FROM orden_trabajo
            WHERE numero_acta = :display
            """
        ),
        {"display": _DEFAULT_SEED_DISPLAY},
    ).mappings().first()
    occupied = int(row["cnt"] or 0) > 0 if row else False
    return {
        "proposed_next_value": _DEFAULT_SEED,
        "proposed_display": _DEFAULT_SEED_DISPLAY,
        "display_occupied": occupied,
        "can_seed": not occupied,
    }


def upgrade() -> None:
    bind = op.get_bind()

    if not _column_exists("orden_trabajo", "numero_secuencia_global"):
        with op.batch_alter_table("orden_trabajo") as batch_op:
            batch_op.alter_column(
                "numero_acta",
                existing_type=sa.String(length=6),
                type_=sa.String(length=10),
                existing_nullable=False,
            )
            batch_op.add_column(sa.Column("numero_secuencia_global", sa.BigInteger(), nullable=True))

    insp = inspect(bind)
    ot_indexes = {idx["name"] for idx in insp.get_indexes("orden_trabajo")}
    if "ix_orden_trabajo_numero_secuencia_global" not in ot_indexes:
        op.create_index(
            "ix_orden_trabajo_numero_secuencia_global",
            "orden_trabajo",
            ["numero_secuencia_global"],
            unique=True,
        )

    if not _table_exists("orden_trabajo_contador"):
        op.create_table(
            "orden_trabajo_contador",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("next_value", sa.BigInteger(), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        )

    if not _table_exists("orden_trabajo_contador_audit"):
        op.create_table(
            "orden_trabajo_contador_audit",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("old_value", sa.BigInteger(), nullable=False),
            sa.Column("new_value", sa.BigInteger(), nullable=False),
            sa.Column("requested_new_value", sa.BigInteger(), nullable=True),
            sa.Column("reason", sa.String(length=500), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    precheck = _precheck_seed(bind)
    if not precheck["can_seed"]:
        raise RuntimeError(
            "OT-AUTO.3 seed precheck FAILED: "
            f"display {_DEFAULT_SEED_DISPLAY} already occupied; "
            "resolve manually before migration."
        )

    existing = bind.execute(text("SELECT id FROM orden_trabajo_contador LIMIT 1")).first()
    if existing is None:
        bind.execute(
            text("INSERT INTO orden_trabajo_contador (next_value) VALUES (:nv)"),
            {"nv": _DEFAULT_SEED},
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists("orden_trabajo_contador_audit"):
        op.drop_table("orden_trabajo_contador_audit")
    if _table_exists("orden_trabajo_contador"):
        op.drop_table("orden_trabajo_contador")

    if _column_exists("orden_trabajo", "numero_secuencia_global"):
        insp = inspect(bind)
        ot_indexes = {idx["name"] for idx in insp.get_indexes("orden_trabajo")}
        if "ix_orden_trabajo_numero_secuencia_global" in ot_indexes:
            op.drop_index("ix_orden_trabajo_numero_secuencia_global", table_name="orden_trabajo")
        with op.batch_alter_table("orden_trabajo") as batch_op:
            batch_op.drop_column("numero_secuencia_global")
            batch_op.alter_column(
                "numero_acta",
                existing_type=sa.String(length=10),
                type_=sa.String(length=6),
                existing_nullable=False,
            )
