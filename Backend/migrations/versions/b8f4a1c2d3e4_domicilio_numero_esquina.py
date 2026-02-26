"""domicilio numero o esquina

Revision ID: b8f4a1c2d3e4
Revises: 9841d79dfa00
Create Date: 2026-02-01 10:12:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b8f4a1c2d3e4"
down_revision = "9841d79dfa00"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("domicilio", schema=None) as batch_op:
        batch_op.add_column(sa.Column("numero_tipo", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("esquina_raw", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("esquina_catalogo_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("esquina_normalizada", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("esquina_norm_status", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("esquina_norm_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("esquina_norm_error", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("esquina_norm_updated_at", sa.DateTime(), nullable=True))

        batch_op.create_index(batch_op.f("ix_domicilio_numero_tipo"), ["numero_tipo"], unique=False)
        batch_op.create_index(batch_op.f("ix_domicilio_esquina_catalogo_id"), ["esquina_catalogo_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_domicilio_esquina_norm_status"), ["esquina_norm_status"], unique=False)
        batch_op.create_foreign_key(
            "fk_domicilio_esquina_catalogo",
            "calle_catalogo",
            ["esquina_catalogo_id"],
            ["id"],
            ondelete="SET NULL",
            onupdate="CASCADE",
        )


def downgrade():
    with op.batch_alter_table("domicilio", schema=None) as batch_op:
        batch_op.drop_constraint("fk_domicilio_esquina_catalogo", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_domicilio_esquina_norm_status"))
        batch_op.drop_index(batch_op.f("ix_domicilio_esquina_catalogo_id"))
        batch_op.drop_index(batch_op.f("ix_domicilio_numero_tipo"))
        batch_op.drop_column("esquina_norm_updated_at")
        batch_op.drop_column("esquina_norm_error")
        batch_op.drop_column("esquina_norm_score")
        batch_op.drop_column("esquina_norm_status")
        batch_op.drop_column("esquina_normalizada")
        batch_op.drop_column("esquina_catalogo_id")
        batch_op.drop_column("esquina_raw")
        batch_op.drop_column("numero_tipo")
