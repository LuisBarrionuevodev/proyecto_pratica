"""seed 2

Revision ID: b960c9de1bbb
Revises: 0a8dd3f8e75b
Create Date: 2026-03-10 15:28:02.407670

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b960c9de1bbb'
down_revision = '0a8dd3f8e75b'
branch_labels = None
depends_on = None


def upgrade() -> None:

    # === Seed inicial de catálogos ===
    catalog_tipo = sa.table(
        "catalog_tipo_actuacion",
        sa.column("nombre", sa.String),
    )
    op.bulk_insert(
        catalog_tipo,
        [
            {"nombre": "INSPECCION"},
            {"nombre": "REINSPECCION"},
            {"nombre": "RATIFICACION DE CLAUSURA"},
            {"nombre": "RATIFICACION DE DECOMISO"},
            {"nombre": "VERIFICAR E INFORMAR"},
            {"nombre": "TRANSPORTE"},
        ],
    )

    catalog_contra = sa.table(
        "catalog_contraproducencia",
        sa.column("nombre", sa.String),
    )
    op.bulk_insert(
        catalog_contra,
        [
            {"nombre": "LOCAL CERRADO"},
            {"nombre": "NO EXISTE/NO ES EL RUBRO"},
            {"nombre": "CLIMA"},
            {"nombre": "ZONA ROJA"},
            {"nombre": "NO_HUBO"},
            {"nombre": "OTROS"},
        ],
    )

    catalog_motivo = sa.table(
        "catalog_motivo_comprobacion",
        sa.column("nombre", sa.String),
    )
    op.bulk_insert(
        catalog_motivo,
        [
            {"nombre": "Falta de Higiene"},
            {"nombre": "Condiciones Edilicias Inadecuadas"},
            {"nombre": "No Permite la Inspección"},
            {"nombre": "Incumplimiento"},
            {"nombre": "Incumplimiento de Notificación"},
            {"nombre": "Sin Certificado de Desinfección"},
            {"nombre": "Sin Carnet de Sanidad"},
            {"nombre": "Sin Certificado de Sanidad"},
            {"nombre": "Mercadería Vencida"},
            {"nombre": "Productos Sin Rotulación"},
        ],
    )


def downgrade() -> None:
    # === Drop catálogos ===
    op.drop_table("catalog_motivo_comprobacion")
    op.drop_table("catalog_contraproducencia")
    op.drop_table("catalog_tipo_actuacion")

    # === Revertir domicilio ===
    op.alter_column("domicilio", "rubro_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("domicilio", "contribuyente_id", existing_type=sa.Integer(), nullable=False)

    # === Revertir OT ===
    op.drop_column("orden_trabajo", "deleted_at")

    # ### end Alembic commands ###
