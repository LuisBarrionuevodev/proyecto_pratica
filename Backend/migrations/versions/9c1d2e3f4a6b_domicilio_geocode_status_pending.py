"""add NORM_PENDING and GEO_PENDING to domicilio_geocode_status

Revision ID: 9c1d2e3f4a6b
Revises: 8b2c3d4e5f6a
Create Date: 2026-02-05 03:10:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "9c1d2e3f4a6b"
down_revision = "8b2c3d4e5f6a"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE domicilio_geocode "
        "MODIFY COLUMN geo_status "
        "ENUM('PENDING','OK','REVIEW','NO_MATCH','ERROR','NORM_PENDING','GEO_PENDING') "
        "NOT NULL DEFAULT 'PENDING'"
    )


def downgrade():
    op.execute(
        "ALTER TABLE domicilio_geocode "
        "MODIFY COLUMN geo_status "
        "ENUM('PENDING','OK','REVIEW','NO_MATCH','ERROR') "
        "NOT NULL DEFAULT 'PENDING'"
    )
