"""seed2

Revision ID: 589c4b79b2fa
Revises: 947292dc2ed4
Create Date: 2026-02-26 15:12:11.702127

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '589c4b79b2fa'
down_revision = '947292dc2ed4'
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