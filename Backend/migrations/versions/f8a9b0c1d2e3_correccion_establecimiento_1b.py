"""V1.1-ESTABLECIMIENTOS-EDICION.1B: nombre_local de ficha y tipo LOCAL de auditoría.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-11-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "establecimiento_operativo",
        sa.Column("nombre_local", sa.String(length=255), nullable=True),
    )
    op.execute(
        "ALTER TABLE correccion_establecimiento_audit "
        "MODIFY COLUMN tipo ENUM('CONTRIBUYENTE','DOMICILIO','AMBOS','LOCAL') NOT NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE correccion_establecimiento_audit "
        "MODIFY COLUMN tipo ENUM('CONTRIBUYENTE','DOMICILIO','AMBOS') NOT NULL"
    )
    op.drop_column("establecimiento_operativo", "nombre_local")
