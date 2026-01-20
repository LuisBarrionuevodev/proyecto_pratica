"""add catalogs and soft delete OT

Revision ID: c8a0f1d2b9a1
Revises: f3a1c12d9b0e
Create Date: 2026-01-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c8a0f1d2b9a1"
down_revision = "f3a1c12d9b0e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === Soft delete en orden_trabajo ===
    op.add_column("orden_trabajo", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    # === Domicilio: permitir null en contribuyente_id y rubro_id ===
    op.alter_column("domicilio", "contribuyente_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("domicilio", "rubro_id", existing_type=sa.Integer(), nullable=True)

    # === Catálogos: tipo, contraproducencia, motivo comprobación ===
    op.create_table(
        "catalog_tipo_actuacion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "catalog_contraproducencia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "catalog_motivo_comprobacion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.UniqueConstraint("nombre"),
    )

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
