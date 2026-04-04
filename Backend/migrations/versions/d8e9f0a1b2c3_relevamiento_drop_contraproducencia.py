"""relevamiento: eliminar columna contraproducencia.

Solo afecta la entidad Relevamiento; catálogos y actuaciones no se modifican.
"""

from alembic import op
import sqlalchemy as sa


revision = "d8e9f0a1b2c3"
down_revision = "c7a1b2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_relevamiento_contraproducencia", table_name="relevamiento")
    op.drop_column("relevamiento", "contraproducencia")


def downgrade() -> None:
    op.add_column(
        "relevamiento",
        sa.Column("contraproducencia", sa.String(length=128), nullable=True),
    )
    op.create_index("ix_relevamiento_contraproducencia", "relevamiento", ["contraproducencia"], unique=False)
