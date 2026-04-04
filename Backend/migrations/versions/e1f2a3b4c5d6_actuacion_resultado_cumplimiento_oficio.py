"""actuaciones: resultado_cumplimiento_oficio (REINSPECCION_OFICIO / Completar trabajo).

Enum nullable: CUMPLE, NO_CUMPLE.
"""

from alembic import op
import sqlalchemy as sa


revision = "e1f2a3b4c5d6"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "actuaciones",
        sa.Column(
            "resultado_cumplimiento_oficio",
            sa.Enum("CUMPLE", "NO_CUMPLE", name="resultado_cumplimiento_oficio_enum"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # MySQL: al borrar la columna se libera el uso del ENUM definido inline.
    op.drop_column("actuaciones", "resultado_cumplimiento_oficio")
