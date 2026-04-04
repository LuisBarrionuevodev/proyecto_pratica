"""relevamiento: columna esta_abierto (nullable).

El campo turno de UI usa la columna existente turno_carga (MANIANA/TARDE).
"""

from alembic import op
import sqlalchemy as sa


revision = "c7a1b2d3e4f5"
down_revision = "b2c8e9f1a3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "relevamiento",
        sa.Column("esta_abierto", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("relevamiento", "esta_abierto")
