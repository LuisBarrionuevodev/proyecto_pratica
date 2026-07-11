"""PR7.2: nombre_fantasia y angulo_esquina opcionales en relevamiento.

Campos nullable para distinguir establecimientos en esquinas sin romper legacy.
Sin constraints únicos ni cambios de lógica de negocio.

Revision ID: b7e8f9a0c1d2
Revises: a1b2c3d4e5f6
Create Date: 2026-07-11

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b7e8f9a0c1d2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("relevamiento", schema=None) as batch_op:
        batch_op.add_column(sa.Column("nombre_fantasia", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("angulo_esquina", sa.String(length=10), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("relevamiento", schema=None) as batch_op:
        batch_op.drop_column("angulo_esquina")
        batch_op.drop_column("nombre_fantasia")
