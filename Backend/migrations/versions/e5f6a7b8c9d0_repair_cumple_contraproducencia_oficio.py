"""Reparación CUMPLE + contraproducencia inconsistente (GESTIÓN-FIX.2C.3).

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None

_COUNT_INCONSISTENTES_SQL = sa.text(
    """
    SELECT COUNT(*) AS cnt
    FROM actuaciones
    WHERE resultado_cumplimiento_oficio = 'CUMPLE'
      AND contraproducencia IS NOT NULL
      AND TRIM(contraproducencia) != ''
    """
)

_REPAIR_SQL = sa.text(
    """
    UPDATE actuaciones
    SET contraproducencia = NULL
    WHERE resultado_cumplimiento_oficio = 'CUMPLE'
      AND contraproducencia IS NOT NULL
      AND TRIM(contraproducencia) != ''
    """
)


def upgrade() -> None:
    bind = op.get_bind()
    count = int(bind.execute(_COUNT_INCONSISTENTES_SQL).scalar() or 0)
    if count:
        print(
            f"GESTIÓN-FIX.2C.3: reparando {count} actuación(es) con "
            "resultado_cumplimiento_oficio=CUMPLE y contraproducencia no nula."
        )
    bind.execute(_REPAIR_SQL)


def downgrade() -> None:
    pass
