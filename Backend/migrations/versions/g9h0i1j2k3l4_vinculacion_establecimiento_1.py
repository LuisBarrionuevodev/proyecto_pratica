"""V1.1-ESTABLECIMIENTOS-VINCULACION.1: tipo VINCULACION en auditoría.

Revision ID: g9h0i1j2k3l4
Revises: f8a9b0c1d2e3
Create Date: 2026-11-15
"""

from __future__ import annotations

from alembic import op

revision = "g9h0i1j2k3l4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Agrega VINCULACION al enum de correccion_establecimiento_audit.tipo."""
    op.execute(
        "ALTER TABLE correccion_establecimiento_audit "
        "MODIFY COLUMN tipo ENUM("
        "'CONTRIBUYENTE','DOMICILIO','AMBOS','LOCAL','VINCULACION'"
        ") NOT NULL"
    )


def downgrade() -> None:
    """Quita VINCULACION del enum (falla si hay filas con ese tipo)."""
    op.execute(
        "ALTER TABLE correccion_establecimiento_audit "
        "MODIFY COLUMN tipo ENUM('CONTRIBUYENTE','DOMICILIO','AMBOS','LOCAL') NOT NULL"
    )
