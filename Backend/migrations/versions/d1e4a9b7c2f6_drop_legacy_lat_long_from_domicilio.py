"""drop legacy lat/long from domicilio

Revision ID: d1e4a9b7c2f6
Revises: c7a4d2e9f1b3
Create Date: 2026-03-17 21:35:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d1e4a9b7c2f6"
down_revision = "c7a4d2e9f1b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Elimina columnas legacy de coordenadas en domicilio.
    La fuente canónica de coordenadas pasa a ser domicilio_geocode.lat/lng.
    """
    with op.batch_alter_table("domicilio") as batch_op:
        batch_op.drop_column("lat")
        batch_op.drop_column("long")


def downgrade() -> None:
    """
    Revierte la eliminación de coordenadas legacy en domicilio.
    """
    with op.batch_alter_table("domicilio") as batch_op:
        batch_op.add_column(sa.Column("lat", sa.Numeric(precision=9, scale=6), nullable=True))
        batch_op.add_column(sa.Column("long", sa.Numeric(precision=9, scale=6), nullable=True))

