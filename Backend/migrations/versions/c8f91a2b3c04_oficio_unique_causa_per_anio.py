"""Oficio: unicidad (causa, anio); misma causa puede repetirse en otros años.

Revision ID: c8f91a2b3c04
Revises: 95941755b426
Create Date: 2026-03-30

"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text
import geoalchemy2

# revision identifiers, used by Alembic.
revision = "c8f91a2b3c04"
down_revision = "95941755b426"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Normalización segura: cadenas vacías / solo espacios → NULL (evita choques con UNIQUE).
    conn.execute(
        text(
            """
            UPDATE oficio
            SET causa = NULL
            WHERE causa IS NOT NULL AND TRIM(causa) = ''
            """
        )
    )

    dup = conn.execute(
        text(
            """
            SELECT causa, anio, COUNT(*) AS n
            FROM oficio
            WHERE causa IS NOT NULL
            GROUP BY causa, anio
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()

    if dup:
        raise RuntimeError(
            "Migración abortada: existen filas en `oficio` con la misma `causa` y el mismo "
            "`anio`. Resolvé manualmente los duplicados antes de reintentar. "
            f"Detalle (causa, año, cantidad): {dup!r}"
        )

    op.create_unique_constraint(
        "uq_of_causa_anio",
        "oficio",
        ["causa", "anio"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_of_causa_anio", "oficio", type_="unique")
