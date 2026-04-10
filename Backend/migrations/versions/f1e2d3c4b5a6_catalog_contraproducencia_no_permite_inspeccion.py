"""seed catalog_contraproducencia NO PERMITE INSPECCION

Garantiza el valor de catálogo usado por Completar trabajo (coerce Pydantic / UI)
en todo entorno que ejecute migraciones, sin duplicados (nombre único).

Revision ID: f1e2d3c4b5a6
Revises: e3f4a5b6c7d8
Create Date: 2026-03-30

"""
from alembic import op
import sqlalchemy as sa


revision = "f1e2d3c4b5a6"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None

_CATALOGO_NOMBRE = "NO PERMITE INSPECCION"


def upgrade():
    """
    Inserta la fila solo si no existe (idempotente ante re-ejecución o seed previo).
    """
    op.execute(
        sa.text(
            """
            INSERT INTO catalog_contraproducencia (nombre)
            SELECT :nombre
            WHERE NOT EXISTS (
                SELECT 1 FROM catalog_contraproducencia WHERE nombre = :nombre
            )
            """
        ).bindparams(nombre=_CATALOGO_NOMBRE)
    )


def downgrade():
    """
    Elimina solo la fila de catálogo con este nombre.
    No modifica actuaciones que ya persistieron el texto en `actuaciones.contraproducencia`.
    """
    op.execute(
        sa.text("DELETE FROM catalog_contraproducencia WHERE nombre = :nombre").bindparams(
            nombre=_CATALOGO_NOMBRE
        )
    )
