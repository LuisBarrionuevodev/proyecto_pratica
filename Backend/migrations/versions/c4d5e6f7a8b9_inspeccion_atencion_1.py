"""V1.1-INSPECCION.1 — atención y contrato de residuos en inspeccion.

Revision ID: c4d5e6f7a8b9
Revises: z1a2b3c4d5e6
Create Date: 2026-11-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c4d5e6f7a8b9"
down_revision = "z1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inspeccion",
        sa.Column("caracter_persona_atendio", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "inspeccion",
        sa.Column(
            "posee_contrato_retiro_residuos_solidos_urbanos",
            sa.Boolean(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("inspeccion", "posee_contrato_retiro_residuos_solidos_urbanos")
    op.drop_column("inspeccion", "caracter_persona_atendio")
