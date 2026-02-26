"""domicilio_geocode addr_hash and source

Revision ID: 8b2c3d4e5f6a
Revises: 7a1c2d3e4f5a
Create Date: 2026-02-05 02:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8b2c3d4e5f6a"
down_revision = "7a1c2d3e4f5a"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("domicilio_geocode", schema=None) as batch_op:
        batch_op.add_column(sa.Column("addr_hash", sa.String(length=40), nullable=True))
        batch_op.add_column(
            sa.Column(
                "source",
                sa.Enum("AUTO", "MANUAL", "REVERSE", name="domicilio_geocode_source"),
                nullable=True,
                server_default="AUTO",
            )
        )


def downgrade():
    with op.batch_alter_table("domicilio_geocode", schema=None) as batch_op:
        batch_op.drop_column("source")
        batch_op.drop_column("addr_hash")
