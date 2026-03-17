"""distrito add codigo stable district number

Revision ID: c7a4d2e9f1b3
Revises: b3f1d9e8a7c6
Create Date: 2026-03-17 19:10:00.000000

"""

from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c7a4d2e9f1b3"
down_revision = "b3f1d9e8a7c6"
branch_labels = None
depends_on = None


_DISTRICT_NUMBER_REGEX = re.compile(r"(\d+)")


def _extract_codigo(nombre: str | None) -> int | None:
    """
    Extrae número de distrito desde el nombre (ej: "Distrito 9" -> 9).
    """
    if not nombre:
        return None
    match = _DISTRICT_NUMBER_REGEX.search(nombre)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def upgrade() -> None:
    """
    Agrega `distrito.codigo` como identificador operativo estable.
    """
    with op.batch_alter_table("distrito") as batch_op:
        batch_op.add_column(sa.Column("codigo", sa.Integer(), nullable=True))
        batch_op.create_index("ix_distrito_codigo", ["codigo"], unique=True)

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, nombre FROM distrito")).mappings().all()
    for row in rows:
        codigo = _extract_codigo(str(row["nombre"]) if row["nombre"] is not None else None)
        if codigo is None:
            continue
        conn.execute(
            sa.text("UPDATE distrito SET codigo = :codigo WHERE id = :district_id"),
            {"codigo": codigo, "district_id": int(row["id"])},
        )


def downgrade() -> None:
    """
    Revierte columna de código estable de distrito.
    """
    with op.batch_alter_table("distrito") as batch_op:
        batch_op.drop_index("ix_distrito_codigo")
        batch_op.drop_column("codigo")

